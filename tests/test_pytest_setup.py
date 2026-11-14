def test_deepeval_pytest_plugin_is_off(pytestconfig):
    # DeepEval's pytest plugin imports DeepEval when pytest starts, with telemetry on,
    # and writes a .deepeval/ folder. evally's tests import it only inside _deepeval_env.
    assert not pytestconfig.pluginmanager.has_plugin("deepeval")
