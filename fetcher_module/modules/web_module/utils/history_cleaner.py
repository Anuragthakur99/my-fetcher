"""History cleaning utility - Framework integrated"""

import json
from pathlib import Path


class HistoryCleaner:
    """Clean browser-use conversation history by removing screenshots and coordinates"""
    
    def __init__(self, session_id: str, logger):
        self.session_id = session_id
        self.logger = logger
        
        # Import web_config directly - always gets updated data
        from ..config.web_config import web_config
        self.web_config = web_config
    
    def clean_history(self, input_path: str, output_path: str) -> str:
        """
        Clean screenshot values and coordinate objects from history JSON file.
        
        Args:
            input_path: Path to the input history JSON file
            output_path: Path for the output cleaned history file
            
        Returns:
            str: Path to the cleaned history file
        """
        self.logger.debug(f"Starting history cleaning process for file: {input_path}")
        
        # Convert to absolute paths
        input_path = Path(input_path).resolve()
        output_path = Path(output_path).resolve()
        
        # Ensure output directory exists (in case it's in a timestamp folder)
        output_dir = output_path.parent
        output_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Using absolute paths - Input: {input_path}, Output: {output_path}")
        
        # Read the history file
        with open(input_path, 'r') as f:
            history_data = json.load(f)
            self.logger.debug(f"Successfully loaded history data from {input_path}")
        
        # Clean screenshots and coordinates in each state
        entry_count = 0
        for entry in history_data['history']:
            entry_count += 1
            # Clean screenshots
            if 'state' in entry and 'screenshot' in entry['state']:
                if entry['state']['screenshot']:
                    entry['state']['screenshot'] = ""
                    self.logger.debug(f"Cleaned screenshot in entry {entry_count}")
            
            # Clean coordinates in interacted elements
            if 'state' in entry and 'interacted_element' in entry['state']:
                for element in entry['state']['interacted_element']:
                    if element and isinstance(element, dict):
                        if 'page_coordinates' in element:
                            element['page_coordinates'] = {}
                        if 'viewport_coordinates' in element:
                            element['viewport_coordinates'] = {}
                        if 'viewport_info' in element:
                            element['viewport_info'] = {}
                        self.logger.debug(f"Cleaned coordinates in entry {entry_count}")
        
        self.logger.info(f"Cleaned {entry_count} entries in history data")
        
        # Write to output file
        with open(output_path, 'w') as f:
            json.dump(history_data, f, indent=2)
            self.logger.info(f"Successfully wrote cleaned history to {output_path}")
            
        return str(output_path)
