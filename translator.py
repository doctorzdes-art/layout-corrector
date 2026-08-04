import re

class LayoutTranslator:
    def __init__(self, config):
        self.config = config
        self._load_mappings()

    def _load_mappings(self):
        # Load active mappings (including overrides) from configuration
        self.en_to_ua, self.en_to_ua_shift, self.ua_to_en, self.ua_to_en_shift = self.config.get_mappings()

    def reload(self):
        self._load_mappings()

    def detect_layout(self, text):
        """
        Returns 'en' if text seems to be typed in English layout (contains mostly English letters),
        or 'ua' if it seems to be typed in Ukrainian layout.
        """
        en_letters = len(re.findall(r'[a-zA-Z]', text))
        ua_letters = len(re.findall(r'[а-яА-ЯіІїЇєЄґҐ]', text))
        
        if en_letters >= ua_letters:
            return 'en'
        else:
            return 'ua'

    def translate(self, text, trigger_shift=False, trigger_caps=False):
        if not text:
            return ""

        # Mappings are reloaded via reload() when settings are saved — no need to rebuild here

        current_caps = trigger_caps
        shift_physical = trigger_shift
            
        # Split text into tokens by whitespace, keeping the spaces
        tokens = re.split(r'(\s+)', text)
        result = []
        prev_direction = 'en'
        
        for token in tokens:
            if not token:
                continue
            if token.isspace():
                result.append(token)
                continue
                
            en_letters = len(re.findall(r'[a-zA-Z]', token))
            ua_letters = len(re.findall(r'[а-яА-ЯіІїЇєЄґҐ]', token))
            
            if en_letters > ua_letters:
                direction = 'en'
                prev_direction = 'en'
            elif ua_letters > en_letters:
                direction = 'ua'
                prev_direction = 'ua'
            else:
                direction = prev_direction
                
            # Infer Caps Lock state at the time of typing this token
            alpha_chars = [c for c in token if c.isalpha()]
            upper_count = sum(1 for c in alpha_chars if c.isupper())
            lower_count = sum(1 for c in alpha_chars if c.islower())
            
            if direction == 'en':
                shifted_punct = set('~{}:"<>?')
                unshifted_punct = set('`[];\',./')
                has_shifted_punct = any(c in shifted_punct for c in token)
                has_unshifted_punct = any(c in unshifted_punct for c in token)
                
                if upper_count > lower_count:
                    if has_shifted_punct and not has_unshifted_punct:
                        inferred_caps = False  # They held Shift for the whole word
                    else:
                        inferred_caps = True   # Default to Caps Lock
                elif upper_count == 0 and lower_count == 0:
                    inferred_caps = current_caps
                elif upper_count == 1 and lower_count == 0:
                    inferred_caps = current_caps
                else:
                    inferred_caps = False
            else:
                if upper_count == 0 and lower_count == 0:
                    inferred_caps = current_caps
                elif upper_count > lower_count:
                    inferred_caps = True
                elif upper_count == 1 and lower_count == 0:
                    inferred_caps = current_caps
                else:
                    inferred_caps = False
                
            translated_token = []
            for char in token:
                if direction == 'en':
                    # Translate EN -> UA
                    mapped = char
                    is_shifted = False
                    if char in self.en_to_ua:
                        mapped = self.en_to_ua[char]
                        is_shifted = False
                    elif char in self.en_to_ua_shift:
                        mapped = self.en_to_ua_shift[char]
                        is_shifted = True
                        
                    if mapped.isalpha():
                        if char.isalpha():
                            # English letter maps to Ukrainian letter. Case is identical.
                            mapped = mapped.upper() if char.isupper() else mapped.lower()
                        else:
                            # English punctuation maps to Ukrainian letter.
                            # Case depends on Caps Lock and whether a shifted punctuation was typed.
                            if inferred_caps != is_shifted:
                                mapped = mapped.upper()
                            else:
                                mapped = mapped.lower()
                            
                    translated_token.append(mapped)
                else:
                    # Translate UA -> EN
                    mapped = char
                    found = False
                    is_shifted = False
                    
                    if char in self.ua_to_en:
                        mapped_val = self.ua_to_en[char]
                        is_shifted = False
                        found = True
                    elif char in self.ua_to_en_shift:
                        mapped_val = self.ua_to_en_shift[char]
                        is_shifted = True
                        found = True
                        
                    if found:
                        if mapped_val.isalpha():
                            # For regular letters (e.g. й -> q, Й -> Q), case is preserved
                            mapped = mapped_val
                        else:
                            # For English punctuation mapped from Ukrainian letters (e.g. х/Х -> [/{)
                            if char.isalpha():
                                shift_held = (char.isupper() != inferred_caps)
                            else:
                                shift_held = is_shifted
                                
                            if shift_held:
                                # We want the shifted punctuation (from ua_to_en_shift)
                                key_char = char.upper() if char.isalpha() else char
                                if key_char in self.ua_to_en_shift:
                                    mapped = self.ua_to_en_shift[key_char]
                                else:
                                    mapped = mapped_val
                            else:
                                # We want the non-shifted punctuation (from ua_to_en)
                                key_char = char.lower() if char.isalpha() else char
                                if key_char in self.ua_to_en:
                                    mapped = self.ua_to_en[key_char]
                                else:
                                    mapped = mapped_val
                    translated_token.append(mapped)
            result.append("".join(translated_token))
            
        return "".join(result)
