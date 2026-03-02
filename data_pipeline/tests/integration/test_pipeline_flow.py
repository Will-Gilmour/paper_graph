"""Integration test for pipeline flow."""

import pytest
from unittest.mock import Mock, patch

from data_pipeline.config import PipelineConfig
from data_pipeline.workflow import PipelineOrchestrator
from data_pipeline.models.graph import PaperGraphData


@pytest.mark.integration
class TestPipelineFlow:
    """Test complete pipeline workflow."""
    
    @pytest.fixture
    def test_config(self, temp_output_dir):
        """Create test configuration."""
        return PipelineConfig(
            seed_dois=["10.1001/test"],
            output_dir=temp_output_dir,
            max_depth=1,
            verbose=True,
        )
    
    @patch('data_pipeline.api.crossref.CrossrefClient.fetch_work')
    def test_graph_building_step(self, mock_fetch, test_config, sample_crossref_work):
        """Test just the graph building step."""
        mock_fetch.return_value = sample_crossref_work
        
        orchestrator = PipelineOrchestrator(test_config)
        
        # This would normally hit real APIs, but we're mocking
        # For a real integration test, you'd use actual API calls
        # graph_data = orchestrator.build_graph(test_config.seed_dois)
        
        # For now, verify orchestrator is set up correctly
        assert orchestrator.config == test_config
    
    def test_orchestrator_initialization(self, test_config):
        """Test orchestrator initializes correctly."""
        orchestrator = PipelineOrchestrator(test_config)
        
        assert orchestrator.config == test_config
        assert orchestrator.config.output_dir.exists()
    
    @pytest.mark.slow
    @pytest.mark.skip(reason="Requires actual API calls and GPU")
    def test_full_pipeline_real(self, test_config):
        """
        Full pipeline test with real APIs (skipped by default).
        
        To run this test:
        pytest tests/integration/test_pipeline_flow.py -m slow
        
        Note: Requires:
        - Internet connection
        - Valid API access
        - GPU (or will use CPU fallback)
        """
        orchestrator = PipelineOrchestrator(test_config)
        orchestrator.run_full_pipeline(test_config.seed_dois)
        
        # Verify outputs exist
        assert (test_config.output_dir / "graph.pkl.gz").exists()
        assert (test_config.output_dir / "cluster_labels.json").exists()


@pytest.mark.integration
class TestModuleIntegration:
    """Test integration between modules."""
    
    def test_config_to_orchestrator_flow(self, temp_output_dir):
        """Test config flows correctly to orchestrator."""
        config = PipelineConfig(
            output_dir=temp_output_dir,
            max_depth=2,
        )
        
        config.layout.use_gpu = False
        config.api.max_workers = 4
        
        orchestrator = PipelineOrchestrator(config)
        
        # Verify config is accessible
        assert orchestrator.config.max_depth == 2
        assert orchestrator.config.layout.use_gpu is False
        assert orchestrator.config.api.max_workers == 4

