"""Simplified AWS Bedrock LLM Service - Pure LLM Factory with Global Session Management"""

import boto3
from typing import List, Optional
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage
from browser_use.llm import ChatAnthropicBedrock
from botocore.config import Config
from ..config_loader.env_selector import EnvironmentSelector
from ..logger import StructuredLogger


class LLMService:
    """
    Simplified AWS Bedrock LLM service focused purely on LLM creation and management.
    
    Features:
    - Global singleton session/client management for resource efficiency
    - Environment-based AWS configuration loading
    - Fresh LLM instance creation with customizable parameters
    - Support for both standard Bedrock and browser-use compatible LLMs
    """
    
    # Global singleton resources shared across all instances
    _shared_boto3_session = None
    _shared_bedrock_client = None
    _aws_profile = None
    _aws_region = None
    _initialized = False
    
    def __init__(self, session_id: str = None):
        """
        Initialize LLM service with optional session ID for logging context.
        
        Args:
            session_id: Optional session identifier for logging context
        """
        self.logger = StructuredLogger(
            "system", 
            "llm", 
            f"llm_service_{session_id}" if session_id else "llm_service"
        )
        
        # Initialize global resources if not already done
        if not LLMService._initialized:
            self._initialize_global_resources()
    
    @classmethod
    def _initialize_global_resources(cls):
        """
        Initialize global AWS resources (session and client) that will be shared
        across all LLMService instances for efficiency.
        """
        try:
            # Load environment configuration
            env_selector = EnvironmentSelector()
            env_config = env_selector.load_config()
            
            # Extract AWS configuration from environment config
            aws_config = env_config.get("AWSBEDROCK", {})
            cls._aws_profile = aws_config.get("profile", "default")
            cls._aws_region = aws_config.get("region", "us-east-1")
            
            # Create shared boto3 session
            cls._shared_boto3_session = boto3.Session(profile_name=cls._aws_profile)
            
            # Configure Bedrock client with extended timeouts for long operations
            bedrock_config = Config(
                read_timeout=600,  # 10 minutes read timeout
                connect_timeout=60,  # 1 minute connect timeout
                retries={'max_attempts': 3}
            )
            
            # Create shared Bedrock client
            cls._shared_bedrock_client = cls._shared_boto3_session.client(
                service_name='bedrock-runtime',
                region_name=cls._aws_region,
                config=bedrock_config
            )
            
            cls._initialized = True
            
            # Log initialization success (using a temporary logger since instance logger may not exist yet)
            temp_logger = StructuredLogger("system", "llm", "initialization")
            temp_logger.info(f"Initialized global LLM resources - Profile: {cls._aws_profile}, Region: {cls._aws_region}")
            
        except Exception as e:
            temp_logger = StructuredLogger("system", "llm", "initialization")
            temp_logger.error(f"Failed to initialize global LLM resources: {str(e)}")
            raise
    
    def create_bedrock_llm(
        self,
        model_id: str,
        temperature: float = 0.1,
        max_tokens: int = 25000,
        top_p: float = 0.9,
        disable_streaming: bool = False
    ) -> ChatBedrockConverse:
        """
        Create a fresh ChatBedrockConverse instance with specified parameters.
        
        Args:
            model_id: Bedrock model identifier
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            disable_streaming: Whether to disable streaming responses
            
        Returns:
            ChatBedrockConverse: Fresh LLM instance
        """
        try:
            llm = ChatBedrockConverse(
                model=model_id,
                provider="anthropic",
                client=self._shared_bedrock_client,  # Use shared client
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                disable_streaming=disable_streaming
            )
            
            self.logger.info(f"Created Bedrock LLM - Model: {model_id}, Temperature: {temperature}, Max Tokens: {max_tokens}, Top P: {top_p}")
            return llm
            
        except Exception as e:
            self.logger.error(f"Failed to create Bedrock LLM: {str(e)}")
            raise
    
    def create_browser_use_llm(
        self,
        model_id: str,
        temperature: float = 0.1,
        max_tokens: int = 25000,
        top_p: float = 0.9,
        stop_sequences: Optional[List[str]] = None
    ) -> ChatAnthropicBedrock:
        """
        Create a fresh browser-use compatible ChatAnthropicBedrock instance.
        
        This creates a browser-use native LLM that's fully compatible with browser-use 0.5.5
        without requiring monkey patches.
        
        Args:
            model_id: Bedrock model identifier
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            stop_sequences: Optional list of stop sequences
            
        Returns:
            ChatAnthropicBedrock: Fresh browser-use compatible LLM instance
        """
        try:
            browser_llm = ChatAnthropicBedrock(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop_sequences,
                session=self._shared_boto3_session,  # Use shared session
                aws_region=self._aws_region
            )
            
            self.logger.info(f"Created browser-use LLM - Model: {model_id}, Temperature: {temperature}, Max Tokens: {max_tokens}, Top P: {top_p}")
            return browser_llm
            
        except Exception as e:
            self.logger.error(f"Failed to create browser-use LLM: {str(e)}")
            raise
    
    def stream_response(
        self,
        llm: ChatBedrockConverse,
        messages: List[BaseMessage],
        print_response: bool = True
    ) -> str:
        """
        Stream response from a given LLM instance and return complete response.
        
        Args:
            llm: The LLM instance to use for streaming
            messages: List of messages (SystemMessage, HumanMessage, etc.)
            print_response: Whether to print response chunks as they stream
            
        Returns:
            str: Complete generated response
        """
        try:
            self.logger.info(f"Streaming LLM response with {len(messages)} messages")
            
            # Stream response and collect chunks
            total_content = ""
            chunk_count = 0
            
            for chunk in llm.stream(messages):
                # Handle Bedrock's different response formats
                if isinstance(chunk.content, list):
                    # Extract text from list format (Bedrock Claude format)
                    chunk_content = ""
                    for content_item in chunk.content:
                        if isinstance(content_item, dict) and content_item.get('type') == 'text':
                            chunk_content += content_item.get('text', '')
                        elif isinstance(content_item, str):
                            chunk_content += content_item
                else:
                    # Handle string format (other providers)
                    chunk_content = chunk.content if chunk.content else ""

                total_content += chunk_content
                chunk_count += 1

                # Print chunk if there's actual content and printing is enabled
                if chunk_content and print_response:
                    print(chunk_content, end='', flush=True)
            
            if print_response and total_content:
                print()  # New line after streaming
            
            self.logger.info(f"Completed streaming response with {len(total_content)} characters in {chunk_count} chunks")
            return total_content
            
        except Exception as e:
            self.logger.error(f"Failed to stream LLM response: {str(e)}")
            raise
    
    @classmethod
    def get_aws_config(cls) -> tuple[str, str]:
        """
        Get the current AWS configuration (profile and region).
        
        Returns:
            tuple: (aws_profile, aws_region)
        """
        if not cls._initialized:
            cls._initialize_global_resources()
        return cls._aws_profile, cls._aws_region
    
    @classmethod
    def reset_global_resources(cls):
        """
        Reset global resources. Useful for testing or configuration changes.
        """
        cls._shared_boto3_session = None
        cls._shared_bedrock_client = None
        cls._aws_profile = None
        cls._aws_region = None
        cls._initialized = False
