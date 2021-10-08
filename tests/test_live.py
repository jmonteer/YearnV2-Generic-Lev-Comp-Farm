from brownie import Contract, Wei, interface, accounts

def test_live(Strategy):
   strat_ms = accounts.at("", force=True)
   vault = Contract("")
   new_strat = strat_ms.deploy()
