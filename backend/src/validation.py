"""
Input validation and sanitization module for Prompt2Frame.

This module provides comprehensive validation for user prompts and generated code
to prevent security vulnerabilities and ensure safe execution.
"""

import re
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class PromptValidator:
    """Validates and sanitizes user prompts."""
    
    # Dangerous patterns that might be used for code injection
    DANGEROUS_PATTERNS = [
        # File system operations
        r'\bopen\s*\(',
        r'\bfile\s*\(',
        r'\bread\s*\(',
        r'\bwrite\s*\(',
        r'\bos\.',
        r'\bpath\.',
        r'__file__',
        r'__path__',
        
        # Network operations
        r'\burllib\b',
        r'\brequests\b',
        r'\bsocket\b',
        r'\bhttp\.',
        r'\bftp\b',
        
        # System/subprocess
        r'\bsubprocess\b',
        r'\bsystem\(',
        r'\bexec\(',
        r'\beval\(',
        r'\bcompile\(',
        r'__import__',
        
        # Database
        r'\bsql\b',
        r'\binsert\b.*\binto\b',
        r'\bselect\b.*\bfrom\b',
        r'\bdrop\b.*\btable\b',
        
        # Code execution
        r'globals\(',
        r'locals\(',
        r'vars\(',
        r'dir\(',
    ]
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> Tuple[bool, str]:
        """
        Validate a user prompt for security and content.
        
        Args:
            prompt: The user's prompt
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check length
        if not prompt or not prompt.strip():
            return False, "Prompt cannot be empty"
        
        if len(prompt) < 3:
            return False, "Prompt is too short (minimum 3 characters)"
        
        if len(prompt) > 500:
            return False, "Prompt is too long (maximum 500 characters)"
        
        # Check for dangerous patterns
        prompt_lower = prompt.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in prompt: {pattern}")
                return False, (
                    "Your prompt contains potentially unsafe content. "
                    "Please rephrase to describe visual animations only."
                )
        
        # Check for excessive punctuation (spam indicator)
        special_char_ratio = sum(c in '!@#$%^&*()_+=' for c in prompt) / len(prompt)
        if special_char_ratio > 0.3:
            return False, "Prompt contains too many special characters"
        
        # Check for repeated characters (spam indicator)
        if re.search(r'(.)\1{10,}', prompt):
            return False, "Prompt contains excessive repeated characters"
        
        return True, ""
    
    @classmethod
    def sanitize_prompt(cls, prompt: str) -> str:
        """
        Sanitize a prompt by removing potentially harmful content.
        
        Args:
            prompt: The raw prompt
            
        Returns:
            Sanitized prompt
        """
        # Remove null bytes
        prompt = prompt.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        prompt = ''.join(char for char in prompt if char.isprintable() or char in '\n\t')
        
        # Normalize whitespace
        prompt = ' '.join(prompt.split())
        
        # Trim to max length
        prompt = prompt[:500]
        
        return prompt.strip()


class CodeSecurityValidator:
    """Enhanced security validation for generated code."""
    
    # Comprehensive list of dangerous operations
    DANGEROUS_OPERATIONS = [
        # File I/O
        'open(', 'file(', 'with open',
        
        # OS operations  
        'os.', 'sys.', 'subprocess.', 'shutil.', 'pathlib.',
        
        # Network
        'urllib', 'requests', 'socket', 'http.',
        
        # Code execution
        'exec', 'eval', 'compile', '__import__',
        'globals()', 'locals()', 'vars()',
        
        # Dangerous imports
        'import os', 'import sys', 'import subprocess',
        'import shutil', 'import requests', 'import urllib',
        'import socket', 'import pickle',
        
        # Shell commands
        'system(', 'popen(', 'shell=',
    ]
    
    # Allowed imports only
    ALLOWED_IMPORTS = [
        'from manim import *',
        'import random',
        'import numpy as np',
        'import math',  # Safe math operations
    ]
    
    @classmethod
    def validate_code_safety(cls, code: str) -> Tuple[bool, str]:
        """
        Validate that generated code is safe to execute.
        
        Args:
            code: The generated Python code
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        # Check for dangerous operations
        code_lower = code.lower()
        for operation in cls.DANGEROUS_OPERATIONS:
            if operation in code_lower:
                logger.error(f"Dangerous operation detected: {operation}")
                return False, f"Code contains forbidden operation: {operation}"
        
        # Validate imports
        import_lines = [line.strip() for line in code.split('\n') 
                       if line.strip().startswith(('import ', 'from '))]
        
        for imp_line in import_lines:
            # Check if it's an allowed import
            is_allowed = any(allowed in imp_line for allowed in cls.ALLOWED_IMPORTS)
            if not is_allowed:
                logger.error(f"Unauthorized import: {imp_line}")
                return False, f"Unauthorized import statement: {imp_line}"
        
        # Check for attempts to access internals
        if '__' in code and any(dangerous in code for dangerous in ['__file__', '__path__', '__dict__', '__class__']):
            return False, "Code attempts to access Python internals"
        
        # Check code length (prevent DoS)
        if len(code) > 10000:
            return False, "Generated code is too large"
        
        # Count class definitions (should be exactly 1 Scene subclass)
        class_count = code.count('class ')
        if class_count < 1:
            return False, "No class definition found"
        if class_count > 3:
            return False, "Too many class definitions"
        
        return True, ""
    
    @classmethod
    def analyze_code_complexity(cls, code: str) -> dict:
        """
        Analyze code complexity to prevent resource exhaustion.
        
        Args:
            code: The generated code
            
        Returns:
            Dict with complexity metrics
        """
        return {
            'line_count': len(code.split('\n')),
            'object_count': code.count('Circle(') + code.count('Square(') + 
                          code.count('Rectangle(') + code.count('Triangle('),
            'animation_count': code.count('self.play('),
            'loop_count': code.count('for ') + code.count('while '),
            'function_count': code.count('def '),
        }
    
    @classmethod
    def validate_code_complexity(cls, code: str) -> Tuple[bool, str]:
        """
        Validate that code complexity is within acceptable limits.
        
        Args:
            code: The generated code
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        metrics = cls.analyze_code_complexity(code)
        
        # Check limits
        if metrics['object_count'] > 30:
            return False, "Too many objects (limit: 30)"
        
        if metrics['animation_count'] > 30:
            return False, "Too many animations (limit: 30)"
        
        if metrics['loop_count'] > 10:
            return False, "Too many loops (limit: 10)"
        
        if metrics['function_count'] > 10:
            return False, "Too many function definitions (limit: 10)"
        
        return True, ""
