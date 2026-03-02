"""Test configuration system."""

import os
import pytest
from pathlib import Path

from data_pipeline.config.settings import (
    PipelineConfig,
    APIConfig,
    LayoutConfig,
    ClusteringConfig,
)


class TestAPIConfig:
    """Test API configuration."""
    
    def test_default_values(self):
        """Test default configuration."""
        config = APIConfig()
        
        assert config.mailto == "your-email@example.com"
        assert config.delay_between_requests == 0.0
        assert config.max_workers == 8
    
    def test_custom_values(self):
        """Test custom configuration."""
        config = APIConfig(
            mailto="test@example.com",
            delay_between_requests=0.5,
            max_workers=4,
        )
        
        assert config.mailto == "test@example.com"
        assert config.delay_between_requests == 0.5
        assert config.max_workers == 4


class TestLayoutConfig:
    """Test layout configuration."""
    
    def test_default_values(self):
        """Test default layout config."""
        config = LayoutConfig()
        
        assert config.use_gpu is True
        assert config.fa2_iterations == 2000
        assert config.barnes_hut_theta == 0.5
    
    def test_custom_gpu_setting(self):
        """Test disabling GPU."""
        config = LayoutConfig(use_gpu=False)
        
        assert config.use_gpu is False


class TestClusteringConfig:
    """Test clustering configuration."""
    
    def test_default_values(self):
        """Test default clustering config."""
        config = ClusteringConfig()
        
        assert config.louvain_resolution == 1.0
        assert config.sub_resolution == 1.0
    
    def test_custom_resolution(self):
        """Test custom resolution."""
        config = ClusteringConfig(
            louvain_resolution=1.5,
            sub_resolution=0.8,
        )
        
        assert config.louvain_resolution == 1.5
        assert config.sub_resolution == 0.8


class TestPipelineConfig:
    """Test complete pipeline configuration."""
    
    def test_default_initialization(self):
        """Test default pipeline config."""
        config = PipelineConfig()
        
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.layout, LayoutConfig)
        assert isinstance(config.clustering, ClusteringConfig)
        assert config.verbose is False
    
    def test_with_seed_dois(self):
        """Test config with seed DOIs."""
        config = PipelineConfig(
            seed_dois=["10.1001/test1", "10.1001/test2"]
        )
        
        assert len(config.seed_dois) == 2
        assert "10.1001/test1" in config.seed_dois
    
    def test_nested_config_access(self):
        """Test accessing nested configs."""
        config = PipelineConfig()
        
        # Modify nested config
        config.layout.use_gpu = False
        config.api.max_workers = 16
        
        assert config.layout.use_gpu is False
        assert config.api.max_workers == 16
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading config."""
        config = PipelineConfig(
            seed_dois=["10.1001/test"],
            max_depth=2,
            verbose=True,
        )
        
        config_file = tmp_path / "config.json"
        config.save_to_file(config_file)
        
        assert config_file.exists()
        
        loaded = PipelineConfig.load_from_file(config_file)
        
        assert loaded.seed_dois == ["10.1001/test"]
        assert loaded.max_depth == 2
        assert loaded.verbose is True

