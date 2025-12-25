"""
Unit tests for input validation and code security.

Tests cover prompt validation, code safety checks, and complexity analysis.
"""

import pytest
from src.validation import (
    PromptValidator,
    CodeSecurityValidator
)


class TestPromptValidator:
    """Test prompt validation logic."""
    
    def test_valid_prompt(self):
        """Test that valid prompts pass validation."""
        is_valid, error = PromptValidator.validate_prompt("A blue circle")
        assert is_valid is True
        assert error == ""
    
    def test_prompt_too_short(self):
        """Test that very short prompts are rejected."""
        is_valid, error = PromptValidator.validate_prompt("hi")
        assert is_valid is False
        assert "too short" in error.lower()
    
    def test_prompt_too_long(self):
        """Test that overly long prompts are rejected."""
        long_prompt = "x" * 501
        is_valid, error = PromptValidator.validate_prompt(long_prompt)
        assert is_valid is False
        assert "too long" in error.lower()
    
    def test_empty_prompt(self):
        """Test that empty prompts are rejected."""
        is_valid, error = PromptValidator.validate_prompt("")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_dangerous_pattern_file_operations(self):
        """Test that file operation attempts are blocked."""
        dangerous_prompts = [
            "Create animation using open()",
            "Read file with file()",
            "Use os.path to access files"
        ]
        for prompt in dangerous_prompts:
            is_valid, error = PromptValidator.validate_prompt(prompt)
            assert is_valid is False
            assert "unsafe" in error.lower()
    
    def test_dangerous_pattern_code_execution(self):
        """Test that code execution attempts are blocked."""
        dangerous_prompts = [
            "Use eval() to execute code",
            "Run exec() with my data",
            "Import subprocess module"
        ]
        for prompt in dangerous_prompts:
            is_valid, error = PromptValidator.validate_prompt(prompt)
            assert is_valid is False
    
    def test_sanitize_prompt(self):
        """Test prompt sanitization."""
        # Test null byte removal
        dirty = "test\x00prompt"
        clean = PromptValidator.sanitize_prompt(dirty)
        assert "\x00" not in clean
        
        # Test whitespace normalization
        dirty = "test   multiple    spaces"
        clean = PromptValidator.sanitize_prompt(dirty)
        assert "  " not in clean
        
        # Test trimming
        dirty = "  test  "
        clean = PromptValidator.sanitize_prompt(dirty)
        assert clean == "test"


class TestCodeSecurityValidator:
    """Test code security validation."""
    
    def test_safe_manim_code(self):
        """Test that valid Manim code passes security checks."""
        code = """from manim import *
import random
import numpy as np

class TestScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
        self.wait(1)
"""
        is_safe, error = CodeSecurityValidator.validate_code_safety(code)
        assert is_safe is True
        assert error == ""
    
    def test_dangerous_import_os(self):
        """Test that os imports are blocked."""
        code = """from manim import *
import os

class TestScene(Scene):
    def construct(self):
        os.system('rm -rf /')
"""
        is_safe, error = CodeSecurityValidator.validate_code_safety(code)
        assert is_safe is False
        assert "import" in error.lower()
    
    def test_dangerous_file_operations(self):
        """Test that file operations are blocked."""
        code = """from manim import *

class TestScene(Scene):
    def construct(self):
        with open('/etc/passwd', 'r') as f:
            data = f.read()
"""
        is_safe, error = CodeSecurityValidator.validate_code_safety(code)
        assert is_safe is False
        assert "open" in error.lower()
    
    def test_complexity_limits(self):
        """Test code complexity validation."""
        # Test object limit
        code_many_objects = """from manim import *
class TestScene(Scene):
    def construct(self):
""" + "\n".join([f"        c{i} = Circle()" for i in range(25)])
        
        is_valid, error = CodeSecurityValidator.validate_code_complexity(code_many_objects)
        assert is_valid is False
        assert "objects" in error.lower()
    
    def test_allowed_math_import(self):
        """Test that math import is allowed."""
        code = """from manim import *
import math
import random
import numpy as np

class TestScene(Scene):
    def construct(self):
        x = math.pi
"""
        is_safe, error = CodeSecurityValidator.validate_code_safety(code)
        assert is_safe is True
