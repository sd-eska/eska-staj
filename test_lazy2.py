class MockEnv:
    def _(self): pass

env = MockEnv()
def test():
    # Positional lazy formatting (single arg)
    var1 = "test"
    msg1 = env._("Status %s", var1)
    
    # Keyword or Dictionary lazy formatting
    msg2 = env._("Status %(type)s is %(stat)s", {'type': 'A', 'stat': 'B'})
    
    # kwargs ?
    # msg3 = env._("Status %(type)s is %(stat)s", type='A', stat='B')
