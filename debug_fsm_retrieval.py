import sys
sys.path.append('.')

from orchestrator import session_store
from contract_engine.contract_engine import ContractStateMachine

def debug_fsm_retrieval():
    print("=== Debug FSM Retrieval ===")
    
    session_id = "01445b6a-bb1e-4c1f-9d42-a6a9e8ce2f6f"
    
    print(f"1. Testing session_id: {session_id}")
    
    stored_fsm = session_store.get_contract_fsm(session_id)
    print(f"2. Retrieved FSM: {stored_fsm}")
    print(f"   Type: {type(stored_fsm)}")
    
    if stored_fsm:
        print(f"   Has 'next' method: {hasattr(stored_fsm, 'next')}")
        print(f"   Has 'context' attribute: {hasattr(stored_fsm, 'context')}")
        
        if hasattr(stored_fsm, 'context'):
            print(f"   Context type: {type(stored_fsm.context)}")
            print(f"   Context has 'next': {hasattr(stored_fsm.context, 'next')}")
            print(f"   Context current_state: {getattr(stored_fsm.context, 'current_state', 'N/A')}")
        
        try:
            print("3. Attempting to call stored_fsm.next()...")
            result = stored_fsm.next("test input")
            print(f"   Success: {result}")
        except Exception as e:
            print(f"   Error: {e}")
            print(f"   Error type: {type(e)}")
    else:
        print("   No stored FSM found")
    
    print("4. Creating fresh FSM for comparison...")
    try:
        fresh_fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        print(f"   Fresh FSM type: {type(fresh_fsm)}")
        print(f"   Fresh FSM has 'next': {hasattr(fresh_fsm, 'next')}")
        print(f"   Fresh FSM context type: {type(fresh_fsm.context)}")
    except Exception as e:
        print(f"   Error creating fresh FSM: {e}")

if __name__ == "__main__":
    debug_fsm_retrieval()
