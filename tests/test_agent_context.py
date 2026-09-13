import agent_context


def test_agent_context_defaults():
    assert agent_context.current_author.get() == "unknown"
    assert agent_context.current_channel.get() == "unknown"
    assert not agent_context.is_public_channel()
    assert not agent_context.is_blocked()


def test_is_public_channel():
    token = agent_context.current_channel.set("public")
    try:
        assert agent_context.is_public_channel()
    finally:
        agent_context.current_channel.reset(token)


def test_is_blocked():
    assert agent_context.is_blocked("someone") == ("someone" in agent_context.BLOCKED_USER_IDS)
