import pytest
from unittest.mock import patch, MagicMock
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.llm_helpers import generate_product_recommendation

class TestContractFlowEnhancements:
    def test_filter_criteria_persistence(self):
        """Test that filter criteria are properly stored in contract parameters"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "GPU", "session_id": "test"})
        
        with patch('contract_engine.llm_helpers.analyze_user_preferences') as mock_analyze:
            mock_analyze.return_value = {
                "preferences": {"budget": "under $2000", "size": "fits in mid-tower"},
                "constraints": ["high performance", "quiet operation"]
            }
            
            fsm.context.update_state("wait_for_preferences")
            result = fsm.next("I want a high performance GPU under $2000 that's quiet")
            
            assert fsm.context.preferences == {"budget": "under $2000", "size": "fits in mid-tower"}
            assert fsm.context.constraints == ["high performance", "quiet operation"]
            assert fsm.contract["parameters"]["preferences"] == {"budget": "under $2000", "size": "fits in mid-tower"}
            assert fsm.contract["parameters"]["constraints"] == ["high performance", "quiet operation"]

    @patch('contract_engine.llm_helpers.client')
    def test_llm_recommendation_generation(self, mock_client):
        """Test LLM recommendation generation for top 5 products"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
            "numbered_products": [
                {"number": 1, "name": "RTX 4090", "price": "$1599", "key_specs": "24GB VRAM, 450W"},
                {"number": 2, "name": "RTX 4080", "price": "$1199", "key_specs": "16GB VRAM, 320W"}
            ],
            "recommendation": {
                "choice": 1,
                "reasoning": "RTX 4090 offers best performance for high-end gaming"
            }
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        products = [
            {"name": "RTX 4090", "price": 1599, "rating": 4.8},
            {"name": "RTX 4080", "price": 1199, "rating": 4.6}
        ]
        
        result = generate_product_recommendation(
            products, 
            {"budget": "under $2000"}, 
            ["high performance"]
        )
        
        assert len(result["numbered_products"]) == 2
        assert result["recommendation"]["choice"] == 1
        assert "RTX 4090" in result["recommendation"]["reasoning"]

    def test_top_5_product_ranking(self):
        """Test that rank_and_select returns top 5 products"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        
        products = [
            {"name": f"GPU {i}", "price": 1000 + i*100, "rating": 4.0 + i*0.1}
            for i in range(10)
        ]
        
        top_products = fsm.rank_and_select(products)
        
        assert len(top_products) == 5
        assert top_products[0]["rating"] >= top_products[1]["rating"]

    @patch('contract_engine.llm_helpers.generate_product_recommendation')
    def test_numbered_selection_flow(self, mock_recommendation):
        """Test numbered selection and recommendation acceptance"""
        mock_recommendation.return_value = {
            "numbered_products": [
                {"number": 1, "name": "RTX 4090", "price": "$1599", "key_specs": "24GB VRAM"},
                {"number": 2, "name": "RTX 4080", "price": "$1199", "key_specs": "16GB VRAM"}
            ],
            "recommendation": {"choice": 1, "reasoning": "Best performance"}
        }
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "GPU", "session_id": "test"})
        
        fsm.context.search_results = [
            {"name": "RTX 4090", "price": 1599, "rating": 4.8},
            {"name": "RTX 4080", "price": 1199, "rating": 4.6}
        ]
        
        fsm.context.update_state("rank_and_select")
        result = fsm.next()
        
        assert "Here are the top 5 options:" in result["ask_user"]
        assert "My recommendation: Option 1" in result["ask_user"]
        assert fsm.context.current_state == "confirm_selection"
        
        result = fsm.next("2")
        assert "RTX 4080" in result["ask_user"]
        assert fsm.context.current_state == "confirm_order"
        assert fsm.context.selected_product["name"] == "RTX 4080"

    def test_recommendation_acceptance(self):
        """Test accepting LLM recommendation with 'yes'"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "GPU", "session_id": "test"})
        
        fsm.context.product_recommendations = {
            "recommendation": {"choice": 1}
        }
        fsm.context.top_products = [
            {"name": "RTX 4090", "price": 1599},
            {"name": "RTX 4080", "price": 1199}
        ]
        
        fsm.context.update_state("confirm_selection")
        result = fsm.next("yes")
        
        assert fsm.context.selected_product["name"] == "RTX 4090"
        assert fsm.context.current_state == "confirm_order"

    def test_invalid_selection_handling(self):
        """Test handling of invalid user selections"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.context.top_products = [{"name": "RTX 4090"}, {"name": "RTX 4080"}]
        fsm.context.update_state("confirm_selection")
        
        result = fsm.next("10")
        assert "Please enter a number between 1 and 2" in result["ask_user"]
        
        result = fsm.next("invalid")
        assert "I didn't understand your selection" in result["ask_user"]

    @patch('contract_engine.llm_helpers.analyze_user_preferences')
    @patch('contract_engine.llm_helpers.generate_product_recommendation')
    @patch('contract_engine.contract_engine.search_product')
    def test_end_to_end_enhanced_flow(self, mock_search, mock_recommend, mock_analyze):
        """Test complete enhanced contract flow from preferences to confirmation"""
        mock_search.return_value = [
            {"name": "RTX 4090", "price": 1599, "rating": 4.8},
            {"name": "RTX 4080", "price": 1199, "rating": 4.6}
        ]
        
        mock_analyze.return_value = {
            "preferences": {"budget": "under $2000"},
            "constraints": ["high performance"]
        }
        
        mock_recommend.return_value = {
            "numbered_products": [
                {"number": 1, "name": "RTX 4090", "price": "$1599", "key_specs": "24GB VRAM"}
            ],
            "recommendation": {"choice": 1, "reasoning": "Best performance"}
        }
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "GPU", "session_id": "test"})
        
        fsm.context.update_state("search")
        fsm.next()
        
        fsm.context.update_state("wait_for_preferences")
        fsm.next("high performance under $2000")
        
        assert fsm.context.current_state == "confirm_selection"

    def test_empty_products_handling(self):
        """Test handling when no products are available"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        
        top_products = fsm.rank_and_select([])
        assert top_products == []
        
        fsm.context.search_results = []
        fsm.context.update_state("rank_and_select")
        result = fsm.next()
        
        assert "No suitable products were found" in result["ask_user"]

    @patch('contract_engine.llm_helpers.client')
    def test_llm_recommendation_fallback(self, mock_client):
        """Test fallback when LLM recommendation fails"""
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        products = [
            {"name": "RTX 4090", "price": 1599, "description": "High-end GPU"},
            {"name": "RTX 4080", "price": 1199, "description": "Mid-range GPU"}
        ]
        
        result = generate_product_recommendation(products, ["performance"], {})
        
        assert len(result["numbered_products"]) == 2
        assert result["recommendation"]["choice"] == 1
        assert "price-to-value ratio" in result["recommendation"]["reasoning"]

    def test_contract_parameters_storage_verification(self):
        """Test that all filter criteria persist in contract parameters"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "laptop", "session_id": "test"})
        
        with patch('contract_engine.llm_helpers.analyze_user_preferences') as mock_analyze:
            mock_analyze.return_value = {
                "preferences": {"budget": "under $1500", "screen_size": "13-15 inches", "weight": "under 3 lbs"},
                "constraints": ["lightweight", "long battery life", "fast processor"]
            }
            
            fsm.context.update_state("wait_for_preferences")
            fsm.next("I need a lightweight laptop under $1500 with long battery life")
            
            contract_prefs = fsm.contract["parameters"]["preferences"]
            contract_constraints = fsm.contract["parameters"]["constraints"]
            
            assert "lightweight" in contract_constraints
            assert "long battery life" in contract_constraints
            assert "fast processor" in contract_constraints
            assert contract_prefs["budget"] == "under $1500"
            assert contract_prefs["screen_size"] == "13-15 inches"
            assert contract_prefs["weight"] == "under 3 lbs"

    def test_fewer_than_5_products_handling(self):
        """Test handling when search returns fewer than 5 products"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "GPU", "session_id": "test"})
        
        products = [
            {"name": "RTX 4090", "price": 1599, "rating": 4.8},
            {"name": "RTX 4080", "price": 1199, "rating": 4.6},
            {"name": "RTX 4070", "price": 899, "rating": 4.4}
        ]
        
        top_products = fsm.rank_and_select(products)
        assert len(top_products) == 3
        
        with patch('contract_engine.llm_helpers.generate_product_recommendation') as mock_recommend:
            mock_recommend.return_value = {
                "numbered_products": [
                    {"number": 1, "name": "RTX 4090", "price": "$1599", "key_specs": "24GB VRAM"},
                    {"number": 2, "name": "RTX 4080", "price": "$1199", "key_specs": "16GB VRAM"},
                    {"number": 3, "name": "RTX 4070", "price": "$899", "key_specs": "12GB VRAM"}
                ],
                "recommendation": {"choice": 2, "reasoning": "Best value for performance"}
            }
            
            fsm.context.search_results = products
            fsm.context.update_state("rank_and_select")
            result = fsm.next()
            
            assert "Here are the top 5 options:" in result["ask_user"]
            assert "My recommendation: Option 2" in result["ask_user"]
            assert "Please enter the number (1-3)" in result["ask_user"]

    def test_no_search_results_handling(self):
        """Test graceful handling when no search results are found"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "nonexistent_product", "session_id": "test"})
        
        fsm.context.search_results = []
        fsm.context.update_state("rank_and_select")
        result = fsm.next()
        
        assert "No suitable products were found" in result["ask_user"]
        assert "try a different search" in result["ask_user"]

    def test_single_product_handling(self):
        """Test handling when only one product is found"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "GPU", "session_id": "test"})
        
        products = [{"name": "RTX 4090", "price": 1599, "rating": 4.8}]
        
        with patch('contract_engine.llm_helpers.generate_product_recommendation') as mock_recommend:
            mock_recommend.return_value = {
                "numbered_products": [
                    {"number": 1, "name": "RTX 4090", "price": "$1599", "key_specs": "24GB VRAM"}
                ],
                "recommendation": {"choice": 1, "reasoning": "Only available option"}
            }
            
            fsm.context.search_results = products
            fsm.context.update_state("rank_and_select")
            result = fsm.next()
            
            assert "Here are the top 5 options:" in result["ask_user"]
            assert "1. RTX 4090" in result["ask_user"]
            assert "My recommendation: Option 1" in result["ask_user"]
            assert "Please enter the number (1-1)" in result["ask_user"]

    def test_numbered_selection_boundary_cases(self):
        """Test boundary cases for numbered selection"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.context.top_products = [
            {"name": "Product 1", "price": 100},
            {"name": "Product 2", "price": 200}
        ]
        fsm.context.update_state("confirm_selection")
        
        result = fsm.next("0")
        assert "Please enter a number between 1 and 2" in result["ask_user"]
        
        result = fsm.next("3")
        assert "Please enter a number between 1 and 2" in result["ask_user"]
        
        result = fsm.next("-1")
        assert "I didn't understand your selection" in result["ask_user"]

    def test_washing_machine_constraint_extraction(self):
        """Test constraint extraction for washing machine specific requirements"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "washing machine", "session_id": "test"})
        
        mock_washing_machines = [
            {"name": "Bosch WAJ28008", "price": 599, "energy_efficiency": "A", "capacity": "7kg"},
            {"name": "Samsung WW80", "price": 899, "energy_efficiency": "B", "capacity": "8kg"}
        ]
        
        with patch('contract_engine.llm_helpers.analyze_user_preferences') as mock_analyze, \
             patch('contract_engine.llm_helpers.filter_products_with_llm') as mock_filter:
            
            mock_analyze.return_value = {
                "preferences": {
                    "price": "below 1600 CHF",
                    "energy_efficiency": "B or better", 
                    "capacity": "at least 6kg"
                },
                "constraints": ["energy efficient", "large capacity", "budget-friendly"]
            }
            
            mock_filter.return_value = mock_washing_machines
            
            fsm.context.search_results = mock_washing_machines
            
            fsm.context.update_state("wait_for_preferences")
            result = fsm.next("Price should be below 1600 chf it should be energy efficient below B, and it should take at least 6kg of laundry")
            
            assert "energy efficient" in fsm.context.constraints
            assert "large capacity" in fsm.context.constraints
            assert fsm.context.preferences["price"] == "below 1600 CHF"
            assert fsm.context.preferences["energy_efficiency"] == "B or better"
            assert fsm.context.preferences["capacity"] == "at least 6kg"
            assert fsm.context.current_state == "confirm_selection"

    @patch('contract_engine.llm_helpers.client')
    def test_preference_extraction_with_real_llm_response(self, mock_client):
        """Test preference extraction with realistic LLM responses"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
            "preferences": {
                "price": "below 1600 CHF",
                "energy_efficiency": "B or better",
                "capacity": "at least 6kg"
            },
            "constraints": ["energy efficient", "large capacity", "quiet operation"]
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        from contract_engine.llm_helpers import analyze_user_preferences
        
        result = analyze_user_preferences(
            "Price should be below 1600 chf it should be energy efficient below B, and it should take at least 6kg of laundry",
            [{"name": "Test Washer", "price": 500}]
        )
        
        assert len(result["preferences"]) == 3
        assert "energy efficient" in result["constraints"]
        assert result["preferences"]["price"] == "below 1600 CHF"
        assert result["preferences"]["energy_efficiency"] == "B or better"
        assert result["preferences"]["capacity"] == "at least 6kg"

    @patch('contract_engine.llm_helpers.client')
    def test_preference_extraction_json_parsing_errors(self, mock_client):
        """Test handling of malformed JSON responses"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
            "preferences": ["energy efficient", "large capacity"
            "constraints": {
                "price": "below 1600 CHF"
            }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        from contract_engine.llm_helpers import analyze_user_preferences
        
        result = analyze_user_preferences(
            "Price should be below 1600 chf",
            [{"name": "Test Washer", "price": 500}]
        )
        
        assert result["preferences"] == {}
        assert result["constraints"] == []

    @patch('contract_engine.llm_helpers.client')
    def test_preference_extraction_with_markdown_formatting(self, mock_client):
        """Test handling of LLM responses with markdown formatting"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''```json
        {
            "preferences": {
                "budget": "under $2000",
                "size": "fits in mid-tower"
            },
            "constraints": ["high performance", "quiet"]
        }
        ```'''
        mock_client.chat.completions.create.return_value = mock_response
        
        from contract_engine.llm_helpers import analyze_user_preferences
        
        result = analyze_user_preferences(
            "I want a high performance GPU under $2000 that's quiet",
            [{"name": "RTX 4090", "price": 1599}]
        )
        
        assert len(result["preferences"]) == 2
        assert "high performance" in result["constraints"]
        assert result["preferences"]["budget"] == "under $2000"

    @patch('contract_engine.llm_helpers.client')
    def test_preference_extraction_api_timeout(self, mock_client):
        """Test handling of API timeouts and errors"""
        mock_client.chat.completions.create.side_effect = Exception("API timeout")
        
        from contract_engine.llm_helpers import analyze_user_preferences
        
        result = analyze_user_preferences(
            "I want a laptop under $1500",
            [{"name": "MacBook Air", "price": 1299}]
        )
        
        assert result["preferences"] == {}
        assert result["constraints"] == []

    def test_preference_extraction_data_validation(self):
        """Test validation of extracted preference data structure"""
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "laptop", "session_id": "test"})
        
        with patch('contract_engine.llm_helpers.analyze_user_preferences') as mock_analyze:
            mock_analyze.return_value = {
                "preferences": "not a dict",
                "constraints": "not a list"
            }
            
            fsm.context.update_state("wait_for_preferences")
            result = fsm.next("I need a laptop")
            
            assert isinstance(fsm.context.preferences, dict)
            assert isinstance(fsm.context.constraints, list)
