import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call
import os

# Adjust import based on how tests are run and PYTHONPATH.
from orchestrator.core import handle, Message
# For mocking PRODUCT_SELECTION_PIPELINE and async_client, we need to patch them where they are defined/imported.
# If PRODUCT_SELECTION_PIPELINE is initialized at module level in orchestrator.core,
# we might need to patch its creation function if direct patching is tricky.

# It's often easier to patch the functions/objects directly where they are used if they are module-level.
# For example, patch 'orchestrator.core.PRODUCT_SELECTION_PIPELINE.run'
# and 'orchestrator.core.ask_document_pipeline'
# and 'orchestrator.core.async_client'

@pytest.fixture(autouse=True) # Autouse to ensure environment variable is set for all tests
def set_openai_api_key():
    # Mock OpenAI API key for tests if components rely on it during initialization
    original_value = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "test_key_for_pytest"
    yield
    if original_value is None:
        del os.environ["OPENAI_API_KEY"]
    else:
        os.environ["OPENAI_API_KEY"] = original_value


@pytest.fixture
def mock_session_store():
    # Patch the individual functions imported directly in orchestrator.core
    with patch('orchestrator.core.get_pending_confirmation') as mock_get, \
         patch('orchestrator.core.set_pending_confirmation') as mock_set, \
         patch('orchestrator.core.clear_pending_confirmation') as mock_clear, \
         patch('orchestrator.core.session_store') as mock_store:
        
        mock_get.return_value = None
        mock_store.get_chat_history.return_value = []
        mock_store.add_chat_message = MagicMock()
        mock_store.save_session = MagicMock()
        
        mock_session_store_obj = MagicMock()
        mock_session_store_obj.get_pending_confirmation = mock_get
        mock_session_store_obj.set_pending_confirmation = mock_set
        mock_session_store_obj.clear_pending_confirmation = mock_clear
        mock_session_store_obj.get_chat_history = mock_store.get_chat_history
        mock_session_store_obj.add_chat_message = mock_store.add_chat_message
        mock_session_store_obj.save_session = mock_store.save_session
        
        yield mock_session_store_obj

@pytest.fixture
def mock_contract_fsm():
    with patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class:
        mock_fsm_instance = MagicMock()
        mock_fsm_instance.next.return_value = {"ask_user": "I found this product: Mock GPU X (Price: 299.99). Would you like to confirm this order?"}
        mock_fsm_instance.context.search_results = [{"name": "Mock GPU X", "price": 299.99}]
        mock_fsm_instance.context.current_state = "search"
        mock_fsm_instance.context.selected_product = None
        mock_fsm_class.return_value = mock_fsm_instance
        yield mock_fsm_instance

@pytest.fixture
def mock_intent_extraction():
    with patch('orchestrator.intent_extractor.extract_user_intent') as mock_extract:
        mock_extract.return_value = {
            "intent_type": "contract",
            "confidence": 0.9,
            "parameters": {"contract_template": "purchase_item.yaml", "extracted_query": "I want to buy a GPU"}
        }
        yield mock_extract


@pytest.fixture
def mock_ask_doc():
    with patch('orchestrator.core.ask_document_pipeline') as mock_ask:
        mock_ask.return_value = "RAG answer: This is a helpful AI assistant."
        yield mock_ask

@pytest.fixture
def mock_openai_chat_completions_create():
    with patch('orchestrator.core.async_client') as mock_client:
        mock_create = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "LLM chat reply."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response
        
        mock_client.chat.completions.create = mock_create
        yield mock_create

@pytest.mark.asyncio
async def test_contract_path_product_found():
    messages = [Message(role="user", content="I want to buy a GPU")]
    session_id = "test_contract_session"
    
    with patch('orchestrator.core.session_store') as mock_session_store, \
         patch('orchestrator.core.async_client') as mock_client, \
         patch('orchestrator.core.ask_document_pipeline') as mock_ask_doc, \
         patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
         patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_extract_criteria, \
         patch('tool_adapter.mock_google.google_shopping_search') as mock_search:
        
        mock_session_store.get_pending_confirmation.return_value = None
        mock_session_store.get_contract_fsm.return_value = None
        mock_session_store.get_chat_history.return_value = []
        mock_session_store.add_chat_message = MagicMock()
        mock_session_store.save_session = MagicMock()
        
        from unittest.mock import AsyncMock
        mock_create = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "LLM chat reply."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response
        mock_client.chat.completions.create = mock_create
        
        mock_ask_doc.return_value = "RAG answer: This is a helpful AI assistant."
        
        mock_extract_criteria.return_value = {
            "specifications": {"type": "GPU", "brand": "NVIDIA"},
            "budget": None,
            "preferences": []
        }
        
        mock_search.return_value = [{"name": "Mock GPU", "price": 299.99}]
        
        mock_fsm_instance = MagicMock()
        mock_fsm_instance.next.return_value = {"ask_user": "I found this product: Mock GPU X (Price: 299.99). Would you like to confirm this order?"}
        mock_fsm_instance.context.current_state = "search"
        mock_fsm_instance.context.selected_product = None
        mock_fsm_class.return_value = mock_fsm_instance
        
        response = await handle(messages, session_id)

        mock_fsm_class.assert_called_once()
        mock_fsm_instance.next.assert_called_once()
        assert "I found this product: Mock GPU X (Price: 299.99)" in response["reply"]
        assert "Would you like to confirm this order?" in response["reply"]
        
        mock_session_store.add_chat_message.assert_any_call(session_id, {"role": "user", "content": "I want to buy a GPU"})
        mock_session_store.add_chat_message.assert_any_call(session_id, {"role": "assistant", "content": response["reply"]})
        mock_session_store.save_session.assert_called_with(session_id)

@pytest.mark.asyncio
async def test_confirmation_yes_path(mock_session_store, mock_contract_fsm, mock_intent_extraction, mock_openai_chat_completions_create, mock_ask_doc):
    session_id = "test_confirm_yes"
    pending_product = {"name": "Mock GPU Y", "price": 350}
    mock_session_store.get_pending_confirmation.return_value = pending_product
    
    # Simulate existing chat history for the artifact
    initial_history = [
        {"role": "user", "content": "I want to buy GPU Y"},
        {"role": "assistant", "content": "Found Mock GPU Y... confirm?"}
    ]
    mock_session_store.get_chat_history.return_value = initial_history

    messages = [Message(role="user", content="yes")]

    # Mock file operations for artifact saving
    with patch('orchestrator.core.os.makedirs') as mock_makedirs, \
         patch('builtins.open', new_callable=MagicMock) as mock_open, \
         patch('orchestrator.core.json.dump') as mock_json_dump:
        
        response = await handle(messages, session_id)

    assert "Great! Order confirmed for Mock GPU Y" in response["reply"]
    mock_makedirs.assert_called_once_with("tmp/contracts", exist_ok=True)
    # Path for artifact includes timestamp, so difficult to assert exact path with mock_open.
    # Check that open was called (implies attempt to write) and json.dump was called.
    assert mock_open.called 
    assert mock_json_dump.called
    
    # Verify the content passed to json.dump
    # args[0] of mock_json_dump.call_args is the first positional argument (the data)
    artifact_data_dumped = mock_json_dump.call_args[0][0]
    assert artifact_data_dumped["session_id"] == session_id
    assert artifact_data_dumped["confirmed_product"] == pending_product
    assert "confirmation_time" in artifact_data_dumped
    assert artifact_data_dumped["chat_history_at_confirmation"] == initial_history # Plus the "yes" message if it was added before this specific get_chat_history call

    mock_session_store.clear_pending_confirmation.assert_called_once_with(session_id)
    mock_session_store.add_chat_message.assert_any_call(session_id, {"role": "user", "content": "yes"})


@pytest.mark.asyncio
async def test_confirmation_no_path(mock_session_store, mock_contract_fsm, mock_intent_extraction, mock_openai_chat_completions_create, mock_ask_doc):
    session_id = "test_confirm_no"
    pending_product = {"name": "Mock GPU Z", "price": 400}
    mock_session_store.get_pending_confirmation.return_value = pending_product
    messages = [Message(role="user", content="no")]

    response = await handle(messages, session_id)

    assert "Okay, the order for Mock GPU Z has been cancelled." in response["reply"]
    mock_session_store.clear_pending_confirmation.assert_called_once_with(session_id)
    mock_session_store.add_chat_message.assert_any_call(session_id, {"role": "user", "content": "no"})


@pytest.mark.asyncio
async def test_rag_path():
    session_id = "test_rag_session"
    messages = [Message(role="user", content="#rag What is this system?")]

    with patch('orchestrator.core.session_store') as mock_session_store, \
         patch('orchestrator.core.async_client') as mock_client, \
         patch('orchestrator.core.ask_document_pipeline') as mock_ask_doc, \
         patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent_extraction:
        
        mock_session_store.get_pending_confirmation.return_value = None
        mock_session_store.get_contract_fsm.return_value = None
        mock_session_store.get_chat_history.return_value = []
        mock_session_store.add_chat_message = MagicMock()
        mock_session_store.save_session = MagicMock()
        
        mock_intent_extraction.return_value = {
            "intent_type": "rag",
            "confidence": 1.0,
            "parameters": {"rag_question": "What is this system?"}
        }
        
        mock_ask_doc.return_value = "RAG answer: This is a helpful AI assistant."

        response = await handle(messages, session_id)

        mock_ask_doc.assert_called_once_with(question="What is this system?")
        assert response["reply"] == "RAG answer: This is a helpful AI assistant."
        mock_session_store.add_chat_message.assert_any_call(session_id, {"role": "user", "content": "#rag What is this system?"})


@pytest.mark.asyncio
async def test_chat_path():
    session_id = "test_chat_session"
    user_message = "Hello, how are you?"
    messages = [Message(role="user", content=user_message)]

    with patch('orchestrator.core.session_store') as mock_session_store, \
         patch('orchestrator.core.async_client') as mock_client, \
         patch('orchestrator.core.ask_document_pipeline') as mock_ask_doc, \
         patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent_extraction:
        
        chat_history_for_llm = [{"role": "user", "content": user_message}]
        mock_session_store.get_pending_confirmation.return_value = None
        mock_session_store.get_contract_fsm.return_value = None
        mock_session_store.get_chat_history.return_value = chat_history_for_llm
        mock_session_store.add_chat_message = MagicMock()
        mock_session_store.save_session = MagicMock()
        
        from unittest.mock import AsyncMock
        mock_create = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "LLM chat reply."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response
        mock_client.chat.completions.create = mock_create
        
        mock_intent_extraction.return_value = {
            "intent_type": "chat",
            "confidence": 0.8,
            "parameters": {}
        }

        response = await handle(messages, session_id)

        mock_client.chat.completions.create.assert_called_once_with(model="gpt-4o", messages=chat_history_for_llm)
        assert response["reply"] == "LLM chat reply."
    mock_ask_doc.assert_not_called()
    mock_session_store.add_chat_message.assert_any_call(session_id, {"role": "user", "content": user_message})

# Add more tests:
# - Test for when RAG_AVAILABLE is False (ask_doc should use dummy, or orchestrator handles it)
# - Test for when PRODUCT_SELECTION_PIPELINE is None (contract path is skipped)
# - Test for when product pipeline finds no product
# - Test for empty message to #rag trigger
# - Test for ambiguous confirmation response
# - Test for errors during pipeline execution or LLM calls (though some are implicitly covered if mocks raise errors)
# - Test for session_id in artifact path sanitization (if you want to be very thorough)
# - Test for when OPENAI_API_KEY is not set and async_client is None (chat path should return error)
# - Test for empty messages list to handle()
# - Test for add_chat_message calls count and order for more complex interactions
# - Test for save_session calls count (should be once per handle call at the end)
# - Test the try-except block for importing contract_engine.contract_pipeline (might be hard to unit test directly)
# - Test the try-except block for importing haystack_pipeline (RAG_AVAILABLE flag)
# - Test the try-except blocks for OpenAI client and Product Selection Pipeline initialization (how handle behaves if they are None)

@pytest.mark.asyncio
async def test_rag_path_rag_unavailable():
    session_id = "test_rag_unavailable"
    messages = [Message(role="user", content="#rag Test question")]
    
    with patch('orchestrator.core.session_store') as mock_session_store, \
         patch('orchestrator.core.async_client') as mock_client, \
         patch('orchestrator.core.RAG_AVAILABLE', False), \
         patch('orchestrator.core.ask_document_pipeline') as mock_dummy_ask_doc, \
         patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent_extraction:
        
        mock_session_store.get_pending_confirmation.return_value = None
        mock_session_store.get_contract_fsm.return_value = None
        mock_session_store.get_chat_history.return_value = []
        mock_session_store.add_chat_message = MagicMock()
        mock_session_store.save_session = MagicMock()
        
        mock_intent_extraction.return_value = {
            "intent_type": "rag",
            "confidence": 1.0,
            "parameters": {"rag_question": "Test question"}
        }
        
        mock_dummy_ask_doc.return_value = "RAG system is currently unavailable due to an import error."

        response = await handle(messages, session_id)
        
        assert response["reply"] == "RAG system is currently unavailable due to an import error."
        mock_dummy_ask_doc.assert_called_once_with(question="Test question")

@pytest.mark.asyncio
async def test_contract_path_pipeline_unavailable():
    session_id = "test_pipeline_unavailable"
    user_message = "I want to buy a GPU"
    messages = [Message(role="user", content=user_message)]
    
    with patch('orchestrator.core.session_store') as mock_session_store, \
         patch('orchestrator.core.async_client') as mock_client, \
         patch('orchestrator.core.ask_document_pipeline') as mock_ask_doc, \
         patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
         patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent_extraction:
        
        chat_history_for_llm = [{"role": "user", "content": user_message}]
        mock_session_store.get_pending_confirmation.return_value = None
        mock_session_store.get_contract_fsm.return_value = None
        mock_session_store.get_chat_history.return_value = chat_history_for_llm
        mock_session_store.add_chat_message = MagicMock()
        mock_session_store.save_session = MagicMock()
        
        mock_create = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Sorry, there was an error trying to find products for you."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response
        mock_client.chat.completions.create = mock_create
        
        mock_intent_extraction.return_value = {
            "intent_type": "contract",
            "confidence": 0.9,
            "parameters": {"contract_template": "purchase_item.yaml", "extracted_query": "I want to buy a GPU"}
        }
        
        mock_fsm_class.side_effect = Exception("FSM initialization failed")

        response = await handle(messages, session_id)
        
        assert response["reply"] == "Sorry, there was an error trying to find products for you."

@pytest.mark.asyncio
async def test_contract_path_no_product_found():
    session_id = "test_no_product_found"
    user_message = "Buy a very specific obscure item"
    messages = [Message(role="user", content=user_message)]

    with patch('orchestrator.core.session_store') as mock_session_store, \
         patch('orchestrator.core.async_client') as mock_client, \
         patch('orchestrator.core.ask_document_pipeline') as mock_ask_doc, \
         patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
         patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_extract_criteria, \
         patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent_extraction:
        
        mock_session_store.get_pending_confirmation.return_value = None
        mock_session_store.get_contract_fsm.return_value = None
        mock_session_store.get_chat_history.return_value = []
        mock_session_store.add_chat_message = MagicMock()
        mock_session_store.save_session = MagicMock()
        mock_session_store.set_contract_fsm = MagicMock()
        
        mock_intent_extraction.return_value = {
            "intent_type": "contract",
            "confidence": 0.9,
            "parameters": {"contract_template": "purchase_item.yaml", "extracted_query": "Buy a very specific obscure item"}
        }
        
        mock_extract_criteria.return_value = {
            "specifications": {"type": "obscure item"},
            "budget": None,
            "preferences": []
        }

        mock_fsm_instance = MagicMock()
        mock_fsm_instance.next.return_value = {"ask_user": "Sorry, I couldn't find a suitable product for your request."}
        mock_fsm_instance.context.search_results = []
        mock_fsm_instance.context.current_state = "no_products"
        mock_fsm_instance.context.selected_product = None
        mock_fsm_class.return_value = mock_fsm_instance

        response = await handle(messages, session_id)

        mock_fsm_instance.next.assert_called_once()
        assert "Sorry, I couldn't find a suitable product" in response["reply"]

@pytest.mark.asyncio
async def test_rag_path_empty_question():
    session_id = "test_rag_empty_q"
    messages = [Message(role="user", content="#rag ")]
    
    with patch('orchestrator.core.session_store') as mock_session_store, \
         patch('orchestrator.core.async_client') as mock_client, \
         patch('orchestrator.core.ask_document_pipeline') as mock_ask_doc, \
         patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent_extraction:
        
        mock_session_store.get_pending_confirmation.return_value = None
        mock_session_store.get_contract_fsm.return_value = None
        mock_session_store.get_chat_history.return_value = []
        mock_session_store.add_chat_message = MagicMock()
        mock_session_store.save_session = MagicMock()
        
        mock_intent_extraction.return_value = {
            "intent_type": "rag",
            "confidence": 1.0,
            "parameters": {"rag_question": ""}
        }
        
        response = await handle(messages, session_id)
        
        assert response["reply"] == "Please provide a question after the #rag trigger."
        mock_ask_doc.assert_not_called()

@pytest.mark.asyncio
async def test_confirmation_ambiguous_response(mock_session_store, mock_contract_fsm, mock_intent_extraction, mock_openai_chat_completions_create, mock_ask_doc):
    session_id = "test_confirm_ambiguous"
    pending_product = {"name": "Mock GPU ABC", "price": 123}
    mock_session_store.get_pending_confirmation.return_value = pending_product
    messages = [Message(role="user", content="maybe later")]

    response = await handle(messages, session_id)

    assert "Sorry, I didn't quite understand. For Mock GPU ABC, please confirm with 'yes' or 'no'." in response["reply"]
    mock_session_store.clear_pending_confirmation.assert_not_called() # Should not clear yet
    mock_session_store.add_chat_message.assert_any_call(session_id, {"role": "user", "content": "maybe later"})

@pytest.mark.asyncio
async def test_empty_messages_list_to_handle(mock_session_store):
    session_id = "test_empty_messages"
    response = await handle(messages=[], session_id=session_id)
    assert "No messages provided to orchestrator" in response["reply"]
    mock_session_store.add_chat_message.assert_not_called() # Should not add if no messages
    mock_session_store.save_session.assert_not_called() # Should not save if early exit
