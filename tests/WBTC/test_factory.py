import brownie

def deploy_new_vault(currency, gov, Vault):
    vault = gov.deploy(Vault)

    vault.initialize(currency, gov, gov, "", "", gov, gov, {"from": gov})
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    return vault

def test_factory_name(factory, strategy):
    assert factory.name() == "FactoryGenLevCompV2@"+strategy.apiVersion()

def test_factory_clone(currency, factory, cToken, gov, strategist, Vault, Strategy, user, weth):
    new_vault = deploy_new_vault(currency, gov, Vault)
    currency.approve(new_vault, 2 ** 256 - 1, {'from': user})
    new_vault.deposit(1e8, {'from': user})
    new_strategy = Strategy.at(factory.cloneLevComp(new_vault, cToken).return_value)
    # send WETH to repay 2 wei+ each flashloan
    weth.transfer(new_strategy, 1e6, {'from': '0xBA12222222228d8Ba445958a75a0704d566BF2C8'})


    new_vault.addStrategy(new_strategy, 10_000, 0, 2 ** 256 - 1, 0, {'from': gov})

    new_strategy.harvest({'from': new_strategy.strategist()})

    assert new_strategy.getCurrentPosition()[0] > 0
    assert new_strategy.getCurrentPosition()[1] > 0

    new_vault.updateStrategyDebtRatio(new_strategy, 0, {'from': gov})

    new_strategy.harvest({'from': new_strategy.strategist()})
    new_strategy.harvest({'from': new_strategy.strategist()})
    assert new_vault.strategies(new_strategy).dict()['totalDebt'] == 0
