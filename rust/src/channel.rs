//! Payment channels and the markup (SPEC.md section 8).

pub const MARKUP_POINTS: u64 = 15;
pub const NOTICE_SLOTS: u64 = 648_000;
pub const VOUCHER_DOMAIN: &[u8] = b"sasona/voucher/v1";
pub const DEVNET: u8 = 1;

/// 8.1: 15% of the price, rounded up.
pub fn markup(price: u64) -> u64 {
    ((price as u128 * MARKUP_POINTS as u128).div_ceil(100)) as u64
}

/// 8.4: the largest amount, at most the voucher's, whose price and markup
/// fit in what was put in.
pub fn payable(voucher: u64, put_in: u64) -> u64 {
    voucher.min((put_in as u128 * 100 / (100 + MARKUP_POINTS) as u128) as u64)
}

/// 8.3: the 90 bytes a voucher's signer signs.
pub fn voucher_message(program: &[u8; 32], cluster: u8, channel: &[u8; 32], amount: u64) -> [u8; 90] {
    let mut m = [0u8; 90];
    m[..17].copy_from_slice(VOUCHER_DOMAIN);
    m[17..49].copy_from_slice(program);
    m[49] = cluster;
    m[50..82].copy_from_slice(channel);
    m[82..].copy_from_slice(&amount.to_be_bytes());
    m
}

#[derive(Debug, PartialEq, Eq)]
pub enum Refused {
    ClosePending,
    NoticeOver,
    NothingMore,
    NothingOwed,
    AlreadyAsked,
    NoticeNotOver,
}

/// A channel as 8.2 to 8.5 keep it. `balance` is what its token account
/// holds, which someone sending dollars to it can make more than the record.
#[derive(Debug, Clone)]
pub struct Channel {
    pub put_in: u64,
    pub balance: u64,
    pub taken: u64,
    pub charged: u64,
    pub owed: u64,
    pub asked: Option<u64>,
}

impl Channel {
    pub fn open(put_in: u64) -> Self {
        Channel { put_in, balance: put_in, taken: 0, charged: 0, owed: 0, asked: None }
    }

    fn in_notice(&self, slot: u64) -> bool {
        self.asked.is_none_or(|a| slot < a + NOTICE_SLOTS)
    }

    pub fn add(&mut self, amount: u64) -> Result<(), Refused> {
        if self.asked.is_some() {
            return Err(Refused::ClosePending);
        }
        self.put_in += amount;
        self.balance += amount;
        Ok(())
    }

    pub fn donate(&mut self, amount: u64) {
        self.balance += amount;
    }

    /// (to the payee, markup charged)
    pub fn pay(&mut self, voucher: u64, slot: u64) -> Result<(u64, u64), Refused> {
        if !self.in_notice(slot) {
            return Err(Refused::NoticeOver);
        }
        let x = payable(voucher, self.put_in);
        if x <= self.taken {
            return Err(Refused::NothingMore);
        }
        let to_payee = x - self.taken;
        let charge = markup(x) - self.charged;
        self.taken = x;
        self.charged += charge;
        self.owed += charge;
        self.balance -= to_payee;
        assert!(self.taken + self.charged <= self.put_in);
        Ok((to_payee, charge))
    }

    pub fn sweep(&mut self) -> Result<u64, Refused> {
        if self.owed == 0 {
            return Err(Refused::NothingOwed);
        }
        let moved = std::mem::take(&mut self.owed);
        self.balance -= moved;
        Ok(moved)
    }

    pub fn ask_to_close(&mut self, slot: u64) -> Result<(), Refused> {
        if self.asked.is_some() {
            return Err(Refused::AlreadyAsked);
        }
        self.asked = Some(slot);
        Ok(())
    }

    /// (markup to the network, back to the payer)
    pub fn close(&mut self, slot: u64, by_payee: bool) -> Result<(u64, u64), Refused> {
        if !by_payee && self.asked.is_none_or(|a| slot < a + NOTICE_SLOTS) {
            return Err(Refused::NoticeNotOver);
        }
        let out = (self.owed, self.balance - self.owed);
        self.balance = 0;
        Ok(out)
    }
}
