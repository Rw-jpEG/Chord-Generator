# main_app.py (updated)
from collections import Counter, defaultdict
import pickle
import json
import random
from typing import List, Optional
from Markov_Chain_For_Chords import MarkovChain, JazzChord
from key_detector import ScaleDetector, Key
from Phrase_Analysis import PhraseAnalyzer, Note
from melody_generator import MelodyGenerator
from model_diagnostics import diagnose_model

class JazzChordGeneratorApp:
    """Main application using pre-trained model"""
    
    def __init__(self, model_path: str = "trained_jazz_model.json"):
        self.markov_chain = MarkovChain(order=4)
        self.scale_detector = ScaleDetector()
        self.phrase_analyzer = PhraseAnalyzer()
        self.melody_generator = MelodyGenerator()
        
        # Load the pre-trained model
        self._load_model_fixed(model_path)
        
        self.diagnose_model()
        # Application state
        self.current_progression = []
        self.current_melody = []
        self.current_key = None
    
    def _load_model_fixed(self, model_path: str):
        """Fixed model loading that ensures transitions are populated"""
        try:
            # Try the fixed loading method
            if hasattr(self.markov_chain, 'load_model_fixed'):
                self.markov_chain.load_model_fixed(model_path)
            else:
                # Fallback to original with diagnostics
                self.markov_chain.load_model(model_path)
                print(f"Diagnostics - Transitions: {len(self.markov_chain.transitions)}")
                print(f"Diagnostics - Probabilities: {len(self.markov_chain._probabilities)}")
                
                # If transitions is empty but probabilities has data, copy over
                if (len(self.markov_chain.transitions) == 0 and 
                    hasattr(self.markov_chain, '_probabilities') and 
                    len(self.markov_chain._probabilities) > 0):
                    
                    print("🔄 Reconstructing transitions from probabilities...")
                    self._reconstruct_transitions_from_probabilities()
                    
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            print("💡 Creating emergency training data...")
            self._create_emergency_training()
    
    def _reconstruct_transitions_from_probabilities(self):
        """Reconstruct transitions dictionary from probabilities"""
        self.markov_chain.transitions = defaultdict(Counter)
        
        for state, probabilities in self.markov_chain._probabilities.items():
            for chord, prob in probabilities.items():
                # Convert probability to approximate count
                count = max(1, int(prob * 100))
                self.markov_chain.transitions[state][chord] = count
        
        print(f"✅ Reconstructed {len(self.markov_chain.transitions)} transitions")
    
    def process_user_melody(self, 
                          melody_notes: List[Note], 
                          creativity: float = 0.5,
                          progression_length: int = 8,
                          use_key_constraints: bool = True) -> List[JazzChord]:
        """
        Process user melody and generate chord progression using pre-trained model
        """
        print("\n" + "="*50)
        print("GENERATING CHORD PROGRESSION")
        print("="*50)
        
        # Step 1: Detect key from melody
        if use_key_constraints:
            self.current_key = self.scale_detector.detect_key(melody_notes)
            print(f"🎵 Detected Key: {self.current_key}")
        else:
            self.current_key = None
            print("🎵 Key constraints: Disabled")
        
        # Step 2: Analyze phrases for better chord placement
        phrases = self.phrase_analyzer.analyze_phrases(melody_notes)
        print(f"📝 Detected {len(phrases)} musical phrases")
        
        # Step 3: Generate progression using pre-trained model
        progression = self._generate_intelligent_progression(
            melody_notes, 
            phrases,
            progression_length, 
            creativity,
            use_key_constraints
        )
        
        self.current_progression = progression
        self.current_melody = melody_notes
        
        return progression
    
    def _generate_intelligent_progression(self,
                                       melody_notes: List[Note],
                                       phrases: List,
                                       length: int,
                                       creativity: float,
                                       use_key_constraints: bool) -> List[JazzChord]:
        """Generate progression using the pre-trained model with musical intelligence"""
        
        # Convert creativity to temperature (your model seems to work well with 0.3-0.7)
        temperature = 0.3 + (creativity * 0.4)
        
        # Choose starting point based on detected key
        start_sequence = self._get_appropriate_start_sequence()
        
        # Generate base progression
        progression = self.markov_chain.generate_sequence(
            length=length,
            temperature=temperature,
            start_sequence=start_sequence
        )
        
        # Apply key constraints if enabled
        if use_key_constraints and self.current_key:
            progression = self._apply_key_awareness(progression, creativity)
        
        # Ensure progression works with melody
        progression = self._harmonize_with_melody(progression, melody_notes)
        
        return progression
    
    def _get_appropriate_start_sequence(self) -> Optional[List[JazzChord]]:
        """Get appropriate starting sequence based on detected key"""
        if not self.current_key or not self.markov_chain.start_states:
            return None
        
        # Try to find a start sequence in the detected key
        key_tonic = self.current_key.tonic
        for state in self.markov_chain.start_states[:5]:  # Check top 5 common starts
            if state and state[0].root == key_tonic:
                return list(state)
        
        # Fallback to most common start
        return list(self.markov_chain.start_states[0]) if self.markov_chain.start_states else None
    
    def _apply_key_awareness(self, progression: List[JazzChord], creativity: float) -> List[JazzChord]:
        """Subtly adjust progression to be more key-appropriate"""
        adjusted_progression = []
        
        for chord in progression:
            # Higher creativity = more freedom from key constraints
            if creativity > 0.7 or not self._chord_fits_key(chord):
                # Keep the original chord for creative modes or non-diatonic chords
                adjusted_progression.append(chord)
            else:
                # For conservative modes, ensure chord fits the key
                adjusted_chord = self.scale_detector.get_closest_diatonic_chord(chord, self.current_key)
                adjusted_progression.append(adjusted_chord)
        
        return adjusted_progression
    
    def _chord_fits_key(self, chord: JazzChord) -> bool:
        """Check if a chord is diatonic to the current key"""
        if not self.current_key:
            return True
        return self.scale_detector.is_chord_in_key(chord, self.current_key, strict=False)
    
    def _harmonize_with_melody(self, progression: List[JazzChord], melody_notes: List[Note]) -> List[JazzChord]:
        """Ensure chords work well with the melody notes"""
        # Simple implementation - in practice you'd want more sophisticated harmony
        if not melody_notes or len(progression) < 2:
            return progression
        
        # For now, return the progression as-is
        # You could add more sophisticated melody-harmony matching here
        return progression
    
    def generate_progression_directly(self, 
                                    length: int = 8, 
                                    temperature: float = 0.5,
                                    key: str = None) -> List[JazzChord]:
        """Generate a progression directly without melody input"""
        start_sequence = None
        if key:
            # Try to start with a chord in the specified key
            for state in self.markov_chain.start_states or []:
                if state and state[0].root == key:
                    start_sequence = list(state)
                    break
        
        progression = self.markov_chain.generate_sequence(
            length=length,
            temperature=temperature,
            start_sequence=start_sequence
        )
        
        self.current_progression = progression
        return progression
    
    def display_progression_analysis(self):
        """Display analysis of the current progression"""
        if not self.current_progression:
            print("No progression generated yet!")
            return
        
        print("\n" + "="*50)
        print("PROGRESSION ANALYSIS")
        print("="*50)
        
        # Show the progression
        progression_str = " | ".join(str(chord) for chord in self.current_progression)
        print(f"🎹 Chord Progression: {progression_str}")
        
        # Analyze chord types
        chord_types = {}
        for chord in self.current_progression:
            chord_types[chord.quality] = chord_types.get(chord.quality, 0) + 1
        
        print(f"\n📊 Chord Analysis:")
        for quality, count in chord_types.items():
            percentage = (count / len(self.current_progression)) * 100
            print(f"   • {quality}: {count} chords ({percentage:.1f}%)")
        
        # Show common jazz progression patterns found
        self._analyze_progression_patterns()
    
    def _analyze_progression_patterns(self):
        """Analyze common jazz progression patterns in the current progression"""
        if len(self.current_progression) < 3:
            return
        
        common_patterns = {
            "ii-V-I": [("m7", "7", "maj7")],
            "ii-V-i": [("m7", "7", "m7")],
            "I-vi-ii-V": [("maj7", "m7", "m7", "7")],
        }
        
        print(f"\n🎯 Jazz Progression Patterns:")
        progression_qualities = [chord.quality for chord in self.current_progression]
        
        for pattern_name, quality_patterns in common_patterns.items():
            for quality_pattern in quality_patterns:
                pattern_length = len(quality_pattern)
                for i in range(len(progression_qualities) - pattern_length + 1):
                    if progression_qualities[i:i+pattern_length] == list(quality_pattern):
                        chords_in_pattern = self.current_progression[i:i+pattern_length]
                        chord_names = [str(chord) for chord in chords_in_pattern]
                        print(f"   • {pattern_name}: {' → '.join(chord_names)}")
                        break

    def diagnose_model(self):
        """Run diagnostics on the loaded model"""
        print("\n" + "="*50)
        print("MODEL DIAGNOSTICS")
        print("="*50)
        
        markov = self.markov_chain
        
        # Check key properties
        print(f"📊 Transitions count: {len(markov.transitions)}")
        print(f"📊 Probabilities count: {len(markov._probabilities)}")
        print(f"📊 Chord vocabulary size: {len(markov.chord_vocab)}")
        print(f"📊 Start states: {len(markov.start_states)}")
        
        # Check if we have actual data
        if len(markov.transitions) == 0:
            print("❌ CRITICAL: Transitions dictionary is EMPTY!")
            print("   The model cannot generate progressions without transitions.")
        else:
            print("✅ Transitions dictionary has data")
        
        # Test if generation works
        print(f"\n🧪 Testing generation:")
        try:
            progression = markov.generate_sequence(length=4, temperature=0.5)
            print(f"   ✅ Generated: {' | '.join(str(chord) for chord in progression)}")
        except Exception as e:
            print(f"   ❌ Generation failed: {e}")
        
        # Check for extended chords in vocabulary
        extended_chords = []
        basic_chords = []
        
        for chord in list(markov.chord_vocab)[:50]:  # Check first 50 chords
            chord_str = str(chord)
            if chord.extensions or any(x in chord_str for x in ['9', '11', '13', 'b9', '#9', '#11', 'b13']):
                extended_chords.append(chord_str)
            else:
                basic_chords.append(chord_str)
        
        print(f"\n🎹 Chord Vocabulary Analysis:")
        print(f"   • Extended chords found: {len(extended_chords)}")
        print(f"   • Basic chords found: {len(basic_chords)}")
        
        if extended_chords:
            print(f"   Sample extended chords:")
            for chord in extended_chords[:5]:
                print(f"     - {chord}")
        else:
            print("   ⚠️  NO extended chords in vocabulary!")
        
        # Test specific state predictions
        print(f"\n🔍 Testing state predictions:")
        test_states = [
            (JazzChord("D", "m7"), JazzChord("G", "7")),
            (JazzChord("C", "maj7"), JazzChord("A", "m7")),
        ]
        
        for test_state in test_states:
            if test_state in markov._probabilities:
                predictions = markov.get_possible_next(test_state, temperature=1.0)
                print(f"   {test_state[0]} → {test_state[1]} → ? :")
                for chord, prob in sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:3]:
                    has_extensions = "YES" if chord.extensions else "NO"
                    print(f"      {chord} (prob: {prob:.3f}) - Extensions: {has_extensions}")
            else:
                print(f"   ⚠️  State {test_state[0]} → {test_state[1]} not found in model")

    def repair_chord_vocabulary_properly(self):
        """PROPERLY fix malformed chord names in the vocabulary"""
        pass
        # print("🔧 PROPERLY Repairing chord vocabulary...")
        
        # # First, let's see what we're actually dealing with
        # print("📋 Original malformed chords:")
        # malformed_chords = []
        # for chord in self.markov_chain.chord_vocab:
        #     chord_str = str(chord)
        #     if any(pattern in chord_str for pattern in ['13b13', '9#9', '9b9', '9m7', 'm79']):
        #         malformed_chords.append(chord_str)
        
        # for chord_str in malformed_chords[:10]:  # Show first 10
        #     print(f"   {chord_str}")
        
        # # Create a completely new vocabulary with properly parsed chords
        # new_vocab = set()
        # repair_map = {}  # Map old chord objects to new ones
        
        # for chord in self.markov_chain.chord_vocab:
        #     chord_str = str(chord)
            
        #     # Skip and properly recreate malformed chords
        #     if "13b13" in chord_str:
        #         # This should be just "13" - the b13 is redundant
        #         root = chord.root
        #         new_chord = JazzChord(root, "13", [])
        #         repair_map[chord] = new_chord
        #         new_vocab.add(new_chord)
        #         print(f"   Fixed: {chord_str} → {new_chord}")
                
        #     elif "9#9" in chord_str:
        #         # This should be "7#9" 
        #         root = chord.root
        #         new_chord = JazzChord(root, "7", ["#9"])
        #         repair_map[chord] = new_chord
        #         new_vocab.add(new_chord)
        #         print(f"   Fixed: {chord_str} → {new_chord}")
                
        #     elif "9b9" in chord_str:
        #         # This should be "7b9"
        #         root = chord.root
        #         new_chord = JazzChord(root, "7", ["b9"])
        #         repair_map[chord] = new_chord
        #         new_vocab.add(new_chord)
        #         print(f"   Fixed: {chord_str} → {new_chord}")
                
        #     elif "9m7" in chord_str:
        #         # This should be "m9" - minor chord with 9th extension
        #         root = chord.root
        #         new_chord = JazzChord(root, "m7", ["9"])
        #         repair_map[chord] = new_chord
        #         new_vocab.add(new_chord)
        #         print(f"   Fixed: {chord_str} → {new_chord}")
                
        #     elif "m79" in chord_str:
        #         # This should be "m9"
        #         root = chord.root
        #         new_chord = JazzChord(root, "m7", ["9"])
        #         repair_map[chord] = new_chord
        #         new_vocab.add(new_chord)
        #         print(f"   Fixed: {chord_str} → {new_chord}")
                
        #     else:
        #         # Keep well-formed chords as-is
        #         new_vocab.add(chord)
        #         repair_map[chord] = chord
        
        # self.markov_chain.chord_vocab = new_vocab
        # print(f"✅ Properly repaired {len(repair_map)} chords")
        
        # # Now repair transitions
        # self._repair_transitions_properly(repair_map)

    def _repair_transitions_properly(self, repair_map):
        """PROPERLY repair transitions using the repair map"""
        pass
        # print("🔧 PROPERLY Repairing transitions...")
        
        # new_transitions = defaultdict(Counter)
        
        # for state, next_chords in self.markov_chain.transitions.items():
        #     # Repair the state
        #     repaired_state = []
        #     for chord in state:
        #         repaired_chord = repair_map.get(chord, chord)
        #         repaired_state.append(repaired_chord)
            
        #     state_tuple = tuple(repaired_state)
            
        #     # Repair the next chords
        #     for chord, count in next_chords.items():
        #         repaired_chord = repair_map.get(chord, chord)
        #         new_transitions[state_tuple][repaired_chord] += count
        
        # self.markov_chain.transitions = new_transitions
        # self.markov_chain._compute_probabilities()
        # print("✅ Transitions properly repaired")

    def _repair_single_chord(self, chord):
        """Repair a single malformed chord"""
        pass
        # chord_str = str(chord)
        
        # if "13b13" in chord_str:
        #     return JazzChord(chord.root, "13", [])
        # elif "9#9" in chord_str:
        #     return JazzChord(chord.root, "7", ["#9"])
        # elif "9b9" in chord_str:
        #     return JazzChord(chord.root, "7", ["b9"])
        # elif "m7" in chord_str and any(ext in chord_str for ext in ['9', '11', '13']):
        #     extensions = []
        #     if '9' in chord_str: extensions.append('9')
        #     if '11' in chord_str: extensions.append('11')
        #     if '13' in chord_str: extensions.append('13')
        #     return JazzChord(chord.root, "m7", extensions)
        # else:
        #     return chord
        
    def test_dissonant_melodies_forced_extensions(self):
        """Test with FORCED extended chord usage"""
        melodies = self._get_dissonant_test_melodies()
        melody_names = [
            "Chromatic Cluster", "Whole Tone Scale", "Tritone Heavy", 
            "Microtonal", "Atonal", "Polytonal", "Cluster Chords",
            "Free Jazz", "Augmented/Diminished", "Mixed Meter"
        ]
        
        print("🧪 TESTING WITH FORCED EXTENDED CHORDS")
        print("=" * 60)
        
        # Use the PROPER repair function
        self.repair_chord_vocabulary_properly()
        
        for i, (melody, name) in enumerate(zip(melodies, melody_names)):
            print(f"\n🎵 Test {i+1}: {name}")
            print(f"   Notes: {[note.pitch for note in melody[:4]]}...")
            
            # Use FORCED extended chord generation
            progression = self.generate_with_forced_extensions(
                length=8, 
                temperature=0.7, 
                min_extended_ratio=0.6  # Force 60% extended chords
            )
            
            chords_str = " | ".join(str(chord) for chord in progression)
            print(f"   🎹 Generated: {chords_str}")
            
            # Enhanced analysis
            self._analyze_progression_detailed(progression)

    def _get_dissonant_test_melodies(self):
        """Get the dissonant test melodies (you can copy from your dissonant_melodies.py)"""
        # Copy the create_dissonant_test_melodies function here or import it
        from melody_tester import create_dissonant_test_melodies
        return create_dissonant_test_melodies()


    def _analyze_progression_detailed(self, progression):
        """Detailed analysis of chord usage"""
        basic_count = 0
        extended_count = 0
        altered_count = 0
        
        chord_types = {}
        
        for chord in progression:
            chord_str = str(chord)
            has_extensions = bool(chord.extensions)
            has_alterations = any(x in chord_str for x in ['#9', 'b9', '#11', 'b13'])
            
            if has_extensions:
                extended_count += 1
            else:
                basic_count += 1
                
            if has_alterations:
                altered_count += 1
            
            # Track chord types
            chord_type = chord.quality
            if chord.extensions:
                chord_type += "(" + ",".join(chord.extensions) + ")"
            chord_types[chord_type] = chord_types.get(chord_type, 0) + 1
        
        total = len(progression)
        
        print(f"   📊 Detailed Analysis:")
        print(f"      • Basic chords: {basic_count}/{total}")
        print(f"      • Extended chords: {extended_count}/{total} ({extended_count/total*100:.0f}%)")
        print(f"      • Altered chords: {altered_count}/{total}")
        
        print(f"      • Chord types:")
        for chord_type, count in sorted(chord_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"        - {chord_type}: {count}")
        
        if extended_count >= total * 0.5:
            print("      ✅ Good extension usage!")
        else:
            print("      ❌ Still low extension usage")

    def generate_with_forced_extensions(self, length=8, temperature=0.7, min_extended_ratio=0.5):
        """Force the use of extended chords"""
        import random
        
        progression = []
        
        # Get lists of chord types
        basic_chords = [c for c in self.markov_chain.chord_vocab if not c.extensions and 
                    not any(x in str(c) for x in ['9', '11', '13', '#', 'b'])]
        extended_chords = [c for c in self.markov_chain.chord_vocab if c not in basic_chords]
        
        print(f"   Available: {len(basic_chords)} basic, {len(extended_chords)} extended chords")
        
        if not extended_chords:
            print("   ⚠️ No extended chords available, using basic generation")
            return self.markov_chain.generate_sequence(length=length, temperature=temperature)
        
        # Start with extended chord if possible
        if extended_chords:
            progression.append(random.choice(extended_chords))
        else:
            progression.append(random.choice(list(self.markov_chain.chord_vocab)))
        
        while len(progression) < length:
            current_extended_ratio = len([c for c in progression if c in extended_chords]) / len(progression)
            
            # If we need more extended chords, force one
            if current_extended_ratio < min_extended_ratio and random.random() < 0.7:
                # Force an extended chord
                next_chord = random.choice(extended_chords)
            else:
                # Use normal Markov generation
                if len(progression) >= self.markov_chain.order:
                    state = tuple(progression[-self.markov_chain.order:])
                    
                    if state in self.markov_chain._probabilities:
                        candidates = self.markov_chain._probabilities[state].copy()
                        
                        # Bias towards extended chords
                        extended_candidates = {chord: prob for chord, prob in candidates.items() 
                                            if chord in extended_chords}
                        
                        if extended_candidates and random.random() < 0.6:
                            # Choose from extended chords
                            chords, probs = zip(*extended_candidates.items())
                            next_chord = random.choices(chords, weights=probs, k=1)[0]
                        else:
                            # Use normal selection
                            chords, probs = zip(*candidates.items())
                            next_chord = random.choices(chords, weights=probs, k=1)[0]
                    else:
                        # Fallback - prefer extended
                        if extended_chords and random.random() < 0.7:
                            next_chord = random.choice(extended_chords)
                        else:
                            next_chord = random.choice(list(self.markov_chain.chord_vocab))
                else:
                    # Fallback for short sequences
                    if extended_chords and random.random() < 0.7:
                        next_chord = random.choice(extended_chords)
                    else:
                        next_chord = random.choice(list(self.markov_chain.chord_vocab))
            
            progression.append(next_chord)
        
        return progression
        
    

# Enhanced interactive demo
def interactive_demo():
    """Interactive demo using the pre-trained model"""
    app = JazzChordGeneratorApp("trained_jazz_model.json")
    
    print("🎹 Jazz Chord Generator (Pre-trained Model)")
    print("=" * 50)
    print("Options:")
    print("1. Generate progression from melody")
    print("2. Generate progression directly") 
    print("3. Test different creativity levels")
    print("4. Run Model Diagnostics")
    print("5. Repair Model & Test Extended Chords")  # NEW OPTION
    print("6. Exit")
    
    while True:
        choice = input("\nChoose option (1-6): ").strip()
        
        if choice == "1":
            # Melody-based generation
            melody = get_melody_input()
            if melody:
                creativity = get_creativity_level()
                progression = app.process_user_melody(melody, creativity=creativity)
                app.display_progression_analysis()
        
        elif choice == "2":
            # Direct progression generation
            length = int(input("Progression length (default 8): ") or "8")
            temp = float(input("Creativity temperature (0.1-1.0, default 0.5): ") or "0.5")
            key = input("Preferred starting key (e.g., C, F, Bb, or leave blank): ").strip()
            key = key if key else None
            
            progression = app.generate_progression_directly(length=length, temperature=temp, key=key)
            app.display_progression_analysis()
        
        elif choice == "3":
            # Test different creativity levels
            print("\n🧪 Testing different creativity levels:")
            temperatures = [0.1, 0.3, 0.5, 0.7, 0.9]
            for temp in temperatures:
                progression = app.generate_progression_directly(temperature=temp)
                chords_str = " | ".join(str(chord) for chord in progression[:6])
                print(f"   Temperature {temp}: {chords_str}...")
        
        elif choice == "4":
            app.diagnose_model()

        elif choice == "5":
            print("\n" + "="*50)
            print("PROPER REPAIR & FORCED EXTENDED CHORDS")
            print("="*50)
            app.test_dissonant_melodies_forced_extensions()
        elif choice == "6":
            break
        else:
            print("Invalid choice!")

def get_melody_input() -> List[Note]:
    """Get melody input from user"""
    print("\n🎵 Enter melody notes (format: C4 0.0 1.0), or 'demo' for demo melody:")
    melody_notes = []
    
    while True:
        user_input = input("Note (pitch start_beat duration): ").strip()
        if user_input.lower() == 'demo':
            from melody_generator import create_melody_for_progression
            demo_progression = [JazzChord("C", "maj7"), JazzChord("G", "7"), JazzChord("F", "maj7")]
            return create_melody_for_progression(demo_progression)
        elif user_input.lower() == 'done':
            break
        else:
            try:
                pitch, start_beat, duration = user_input.split()
                note = Note(pitch, float(start_beat), float(duration))
                melody_notes.append(note)
                print(f"Added: {note}")
            except:
                print("Invalid format! Use: C4 0.0 1.0")
    
    return melody_notes

def get_creativity_level() -> float:
    """Get creativity level from user"""
    levels = {
        "1": 0.1,  # Very conservative
        "2": 0.3,  # Conservative  
        "3": 0.5,  # Balanced
        "4": 0.7,  # Creative
        "5": 0.9,  # Very creative
    }
    
    print("\n🎨 Choose creativity level:")
    print("1. Very Conservative (follows patterns closely)")
    print("2. Conservative (mostly follows patterns)")
    print("3. Balanced (mix of common and unusual choices)")
    print("4. Creative (more unexpected choices)")
    print("5. Very Creative (highly experimental)")
    
    choice = input("Choice (1-5, default 3): ").strip()
    return levels.get(choice, 0.5)

if __name__ == "__main__":
    interactive_demo()