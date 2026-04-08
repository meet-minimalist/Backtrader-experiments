import backtrader as bt

class ZerodhaDeliveryCommission(bt.CommInfoBase):
    """
    Zerodha equity delivery charges (buy one day, sell another).
    All rates as of April 2026.
    """
    params = (
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_PERC),
    )

    # ── Zerodha brokerage ──────────────────────────────────
    BROKERAGE_RATE = 0.0          # delivery is FREE
    BROKERAGE_CAP  = 20.0         # ₹20 cap (not used for delivery)

    # ── STT (both sides for delivery) ─────────────────────
    STT_RATE       = 0.001        # 0.1% on buy & sell

    # ── Exchange transaction charges (NSE) ────────────────
    ETC_RATE       = 0.0000297    # 0.00297% (NSE equity)

    # ── SEBI turnover charges ──────────────────────────────
    SEBI_RATE      = 0.000001     # ₹10 per crore = 0.0001%

    # ── GST on (brokerage + ETC + SEBI) ───────────────────
    GST_RATE       = 0.18

    # ── Stamp duty (buy side only) ─────────────────────────
    STAMP_BUY_RATE = 0.00015      # 0.015%

    # ── DP charge (sell side only, per transaction) ────────
    DP_CHARGE      = 15.34        # ₹15.34 flat per scrip per sell day

    def _getcommission(self, size, price, pseudoexec):
        turnover = abs(size) * price

        # Brokerage: ₹0 for delivery
        brokerage = 0.0

        # STT: 0.1% on this side
        stt = turnover * self.STT_RATE

        # Exchange + SEBI
        etc  = turnover * self.ETC_RATE
        sebi = turnover * self.SEBI_RATE

        # GST on brokerage + etc + sebi
        gst = (brokerage + etc + sebi) * self.GST_RATE

        # Stamp duty only on buys (size > 0)
        stamp = (turnover * self.STAMP_BUY_RATE) if size > 0 else 0.0

        # DP charge only on sells (size < 0)
        dp = self.DP_CHARGE if size < 0 else 0.0

        total = brokerage + stt + etc + sebi + gst + stamp + dp
        return total

