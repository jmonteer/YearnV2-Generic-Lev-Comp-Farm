import pytest

# deposit 50000 USDC and leverage it according to the collateralTarget
def test_simple(vault, strategy, currency, comp, user, gov, chain):
    currency.approve(vault, 2 ** 256 - 1, {'from': user})
    vault.deposit(50_000 * 1e6, {'from': user})
    
    strategy.harvest({'from': gov})

    deposits, borrows = strategy.getCurrentPosition()
    collat = borrows/deposits

    while(collat < (strategy.collateralTarget()-1e15)/1e18):
        strategy.harvest({'from': gov})
        deposits, borrows = strategy.getCurrentPosition()
        collat = borrows/deposits
        print(f"New Collat {collat}")

    real_assets = deposits - borrows
    assert real_assets >= vault.strategies(strategy).dict()['totalDebt']-1
    assert deposits/real_assets == pytest.approx(3.8461, rel=1e-2) # 3.84x leverage (74% LTV)

    chain.sleep(10 * 24 * 3600)
    chain.mine(1500)

    # debt ratio to 0
    vault.updateStrategyDebtRatio(strategy, 0, {'from': gov})

    # first harvest will be needed for sure
    strategy.harvest({'from': gov})
    deposits, borrows = strategy.getCurrentPosition()
    while(deposits > 1e3):
        deposits, borrows = strategy.getCurrentPosition()
        strategy.harvest({'from': gov})

    # one more harvest to get the debt back to the vault
    strategy.harvest({'from': gov}) 
    assert vault.strategies(strategy).dict()['totalDebt'] < 1e3

def test_huge_deposit(vault, strategy, currency, user, chain, gov):
    currency.approve(vault, 2 ** 256 - 1, {'from': user})
    vault.deposit(35_000_000 * 1e6, {'from': user})

    strategy.harvest({'from': gov})
    deposits, borrows = strategy.getCurrentPosition()
    collat = borrows/deposits

    while(collat < (strategy.collateralTarget()-1e15)/1e18):
        strategy.harvest({'from': gov})
        deposits, borrows = strategy.getCurrentPosition()
        collat = borrows/deposits
        print(f"New Collat {collat}")

    real_assets = deposits - borrows
    assert real_assets >= vault.strategies(strategy).dict()['totalDebt']
    assert deposits/real_assets == pytest.approx(3.8461, rel=1e-2) # 3.8461x leverage

    print("Sleeping and mining some blocks")
    chain.sleep(10 * 24 * 3600)
    chain.mine(1500)

    # to avoid mining more blocks until it reaches default value
    strategy.setMinCompToSell(1e10, {'from': gov})
    # debt ratio to 0
    vault.updateStrategyDebtRatio(strategy, 0, {'from': gov})

    # first harvest will be needed for sure
    strategy.harvest({'from': gov})
    deposits, borrows = strategy.getCurrentPosition()
    while(deposits > 1e3):
        deposits, borrows = strategy.getCurrentPosition()
        strategy.harvest({'from': gov})

    assert vault.strategies(strategy).dict()['totalDebt'] < 1e3
