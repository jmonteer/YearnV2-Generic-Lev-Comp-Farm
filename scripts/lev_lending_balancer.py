import brownie


def balance():
    vault = Contract("")
    strat_comp = Contract("")
    strat_aave = Contract("")

    total_ratio = 5000

    # calculate total funds
    taum = vault.totalAssets()
    max_bps = 10000
    available_funds = taum * total_ratio / max_bps

    print(f"Current AAVE APR: ")

    print(f"Current COMP APR: ")

    # APR_a = APR_c
    # APR_a = 

# AAVE params
aave = interface.IProtocolDataProvider("0x057835Ad21a177dbdd3090bB1CAE03EaCF78Fc6d")
lm = interface.IAaveIncentivesController("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
aave_token = interface.ERC20("0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
stkaave_token = interface.ERC20("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
uniswap_router = interface.IUniswapV2Router02(
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
)

strategies = {
    "yfi-043": "0x66252E6ff02c45f00fBc071c2F3Cf0eb13B2dE19",
    "wbtc-035": "0x4155f2aDc918EEba038C31772027A2eF15DbD73c",
    "dai-043": "0x1D371Ae86c8316917373Ec572B18776655Fd11b7",
}

pessimism_factor = 0.95
seconds_per_block = 13
blocks_per_year = int(3600 * 24 * 365 / seconds_per_block)
safety_margin_bps = 200
skip = [
    "BAT",
    "ZRX",
    "COMP",
    "ENJ",
    "KNC",
    "MANA",
    "REN",
    "BAL",
    "DPI",
    "xSUSHI",
    "CRV",
]

sell_stkaave = False
# AAVE functions
def aave_netWantPerYear(underlying, equity, ltv):
    stkaave_per_week = _aavePerSecond(underlying, equity, ltv) * (7 * 24 * 3600)
    aave_per_week = _best_stkaave_fee_price(
        stkaave_per_week
    )[1] if sell_stkaave else stkaave_per_week
    want_per_week = _priceCheck(aave_token, underlying, aave_per_week)
    interest_per_year = aave_netInterestAccrualPerYear(underlying, equity, ltv)
    return interest_per_year + (want_per_week * 52)

def _aavePerSecond(underlying, targetEquity, ltv):
    (targetSupplied, targetBorrowed) = _supply_borrow(targetEquity, ltv)

    (aToken, _, variableToken) = aave.getReserveTokensAddresses(underlying)
    aToken = interface.ERC20(aToken)
    variableToken = interface.ERC20(variableToken)

    aTokenTotalSupply = targetSupplied + aToken.totalSupply()
    variableTokenTotalSupply = targetBorrowed + variableToken.totalSupply()

    aToken_aave_per_sec = lm.getAssetData(aToken)[1]
    variableToken_aave_per_sec = lm.getAssetData(variableToken)[1]

    aave_per_second = (targetSupplied * aToken_aave_per_sec / aTokenTotalSupply) + (
        targetBorrowed * variableToken_aave_per_sec / variableTokenTotalSupply
    )
    return aave_per_second


def _netInterestAccrualPerYear(asset, targetEquity, ltv):
    (targetSupplied, targetBorrowed) = _supply_borrow(targetEquity, ltv)
    data = aave.getReserveData(asset).dict()
    return (targetSupplied * data["liquidityRate"] / 1e27) - (
        targetBorrowed * data["variableBorrowRate"] / 1e27
    )


def _supply_borrow(equity, ltv):
    targetSupplied = equity * 1e18 / (1e18 - ltv)
    targetBorrowed = (targetSupplied * ltv) / 1e18
    return (targetSupplied, targetBorrowed)

# COMP params
compound = interface.Compound("0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B")
weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
comp = interface.ERC20("0xc00e94Cb662C3520282E6f5717214004A7f26888")
uniswap_router = interface.IUniswapV2Router02(
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
)
cether = "0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5"

pessimism_factor = 0.95
seconds_per_block = 13
blocks_per_year = int(3600 * 24 * 365 / seconds_per_block)  # 2102400


# COMP functions
def comp_netWantPerYear(cToken, strategy=None, increased_equity=0):
    comp_per_block = _compPerBlock(cToken, strategy, increased_equity)
    underlying = cToken.underlying() if cToken.address != cether else weth
    want_per_block = _priceCheck(comp, underlying, comp_per_block)
    if not strategy == None:
        increased_equity += (
            interface.Vault(strategy.vault()).strategies(strategy).dict()["totalDebt"]
        )
    interest_per_block = comp_netInterestAccrualPerBlock(
        cToken,
        increased_equity,
        strategy.collateralTarget() if not strategy == None else None,
    )
    net_per_block = want_per_block + interest_per_block
    return net_per_block * blocks_per_year

def _compPerBlock(cToken, strat=None, increased_equity=0):
    deposits = borrows = 0

    (_, collateralFactor, _) = compound.markets(cToken)
    targetCollat = collateralFactor - (0.02 * 1e18)

    if not strat == None:
        (deposits, borrows) = strat.getCurrentPosition()
        targetCollat = strat.collateralTarget()
        increased_equity += interface.ERC20(strat.want()).balanceOf(strat)

    increased_supply = increased_equity * 1e18 / (1e18 - targetCollat)
    increased_borrow = increased_supply * targetCollat / 1e18

    totalBorrow = cToken.totalBorrows() + increased_borrow

    totalSupplyCtoken = cToken.totalSupply()
    totalSupply = (
        (totalSupplyCtoken * cToken.exchangeRateStored()) / 1e18
    ) + increased_supply

    blockShareSupply = 0
    if totalSupply > 0:
        blockShareSupply = (
            (deposits + increased_supply) * compound.compSupplySpeeds(cToken)
        ) / totalSupply

    blockShareBorrow = 0
    if totalBorrow > 0:
        blockShareBorrow = (
            (borrows + increased_borrow) * compound.compBorrowSpeeds(cToken)
        ) / totalBorrow

    blockShare = blockShareSupply + blockShareBorrow

    return blockShare

def comp_netInterestAccrualPerBlock(cToken, targetEquity, targetCollat=None):
    if targetCollat == None:
        (_, collateralFactor, _) = compound.markets(cToken)
        targetCollat = collateralFactor - (0.02 * 1e18)
    targetSupplied = targetEquity / (1e18 - targetCollat)
    targetBorrowed = (targetSupplied * targetCollat) / 1e18
    return (targetSupplied * cToken.supplyRatePerBlock()) - (
        targetBorrowed * cToken.borrowRatePerBlock()
    )


