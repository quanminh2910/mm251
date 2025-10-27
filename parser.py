import xml.etree.ElementTree as ET

class Place:
    def __init__(self, place_id, initial_marking=0):
        self.id = place_id
        self.initial_marking = initial_marking
        
    def __repr__(self):
        # This helps with debugging
        return f"Place(id='{self.id}', marking={self.initial_marking})"

class Transition:
    def __init__(self, trans_id):
        self.id = trans_id
        self.inputs = []  # A list of Place objects
        self.outputs = [] # A list of Place objects

    def __repr__(self):
        # This helps with debugging
        return f"Transition(id='{self.id}')"

class PetriNet:
    def __init__(self):
        # We use dictionaries for fast lookups by ID
        self.places = {}      # Key: place_id, Value: Place object
        self.transitions = {} # Key: trans_id, Value: Transition object
        
    def get_initial_marking_vector(self):
        # This will be useful for Task 2
        # Returns a simple list of 0s and 1s
        # Note: We must guarantee the order is always the same!
        sorted_places = sorted(self.places.values(), key=lambda p: p.id)
        return [p.initial_marking for p in sorted_places]

def parse_pnml(file_path):
    """
    Parses a 1-safe PNML file and returns a PetriNet object.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return None
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None

    net = PetriNet()

    # Find the first <net> tag. The {*
    # } is a wildcard for the namespace.
    net_element = root.find('.//{*}net')
    if net_element is None:
        print("Error: Could not find <net> tag in PNML file.")
        return None

    # --- 1. Find all places ---
    for place_elem in net_element.findall('.//{*}place'):
        place_id = place_elem.get('id')
        if not place_id:
            continue
            
        initial_marking = 0
        # Find the initial marking. For 1-safe nets, it's 0 or 1.
        marking_node = place_elem.find('.//{*}initialMarking/{*}text')
        if marking_node is not None and marking_node.text:
            try:
                initial_marking = int(marking_node.text)
            except ValueError:
                initial_marking = 0 # Default if text is not a number
        
        net.places[place_id] = Place(place_id, initial_marking)

    # --- 2. Find all transitions ---
    for trans_elem in net_element.findall('.//{*}transition'):
        trans_id = trans_elem.get('id')
        if not trans_id:
            continue
            
        net.transitions[trans_id] = Transition(trans_id)

    # --- 3. Find all arcs and connect them ---
    for arc_elem in net_element.findall('.//{*}arc'):
        arc_id = arc_elem.get('id')
        source_id = arc_elem.get('source')
        target_id = arc_elem.get('target')

        if not (arc_id and source_id and target_id):
            print(f"Warning: Skipping incomplete arc (id={arc_id})")
            continue
            
        # --- This is your consistency check ---
        if source_id not in net.places and source_id not in net.transitions:
            print(f"Error: Arc '{arc_id}' has unknown source '{source_id}'")
            continue
        if target_id not in net.places and target_id not in net.transitions:
            print(f"Error: Arc '{arc_id}' has unknown target '{target_id}'")
            continue

        # --- Logic for connecting nodes ---
        
        # Case 1: Place -> Transition
        if source_id in net.places and target_id in net.transitions:
            place = net.places[source_id]
            transition = net.transitions[target_id]
            transition.inputs.append(place)
        
        # Case 2: Transition -> Place
        elif source_id in net.transitions and target_id in net.places:
            transition = net.transitions[source_id]
            place = net.places[target_id]
            transition.outputs.append(place)
        
        else:
            # This handles invalid arcs, e.g., Place-to-Place
            print(f"Warning: Skipping invalid arc from '{source_id}' to '{target_id}'")

    print(f"Successfully parsed PNML file.")
    print(f"Found {len(net.places)} places and {len(net.transitions)} transitions.")
    return net


# --- Example Usage ---
if __name__ == "__main__":
    
    # Create a dummy PNML file for testing
    dummy_pnml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <pnml xmlns="http://www.pnml.org/version-2009/grammar/pnml">
      <net id="net1" type="http://www.pnml.org/version-2009/grammar/ptnet">
        <page id="page1">
          <place id="p1">
            <initialMarking><text>1</text></initialMarking>
          </place>
          <place id="p2">
            <initialMarking><text>0</text></initialMarking>
          </place>
          <transition id="t1">
          </transition>
          <arc id="a1" source="p1" target="t1"/>
          <arc id="a2" source="t1" target="p2"/>
        </page>
      </net>
    </pnml>
    """
    
    # Write the dummy content to a file
    with open("test_net.pnml", "w") as f:
        f.write(dummy_pnml_content)

    # Now, parse the file we just created
    petri_net = parse_pnml("test_net.pnml")

    if petri_net:
        # Check if the parser worked
        print("\n--- Parse Results ---")
        
        # Print places
        for place in petri_net.places.values():
            print(place)
            
        # Print transitions and their connections
        for trans in petri_net.transitions.values():
            print(f"\nTransition: {trans.id}")
            print(f"  Inputs: {[p.id for p in trans.inputs]}")
            print(f"  Outputs: {[p.id for p in trans.outputs]}")

        # Test the initial marking vector
        print("\nInitial Marking Vector:")
        print(petri_net.get_initial_marking_vector())