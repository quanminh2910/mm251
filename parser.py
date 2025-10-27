import xml.etree.ElementTree as ET
import xml.etree.ElementTree as ET
import time
import collections # We need this for the queue

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
        self.places = {}      # Key: place_id, Value: Place object
        self.transitions = {} # Key: trans_id, Value: Transition object
        
        # --- NEW properties for Task 2 ---
        # We need a fixed, sorted order of places to create
        # marking vectors/tuples consistently.
        self.sorted_place_ids = []
        
        # A lookup map for {place_id -> index} in the vector
        self.place_id_to_index = {}

    def finalize_structure(self):
        """
        Call this *after* parsing is complete.
        It builds the sorted lists and maps needed for the BFS.
        """
        self.sorted_place_ids = sorted(self.places.keys())
        self.place_id_to_index = {pid: i for i, pid in enumerate(self.sorted_place_ids)}
        print("PetriNet structure finalized. Ready for analysis.")

    def get_initial_marking_tuple(self):
        """
        Returns the initial marking as a hashable tuple.
        e.g., (1, 0, 0)
        """
        # Create a list of 0s first
        marking = [0] * len(self.sorted_place_ids)
        
        # Set the initial markings
        for place_id, place_obj in self.places.items():
            if place_obj.initial_marking == 1:
                index = self.place_id_to_index[place_id]
                marking[index] = 1
                
        return tuple(marking)

    def get_enabled_transitions(self, marking_tuple):
        """
        Given a marking, returns a list of all enabled Transition objects.
        """
        enabled = []
        for trans in self.transitions.values():
            is_enabled = True
            
            # Check if all input places have a token
            for in_place in trans.inputs:
                place_index = self.place_id_to_index[in_place.id]
                if marking_tuple[place_index] == 0:
                    is_enabled = False
                    break # This transition is not enabled
            
            if is_enabled:
                enabled.append(trans)
                
        return enabled

    def fire_transition(self, marking_tuple, transition):
        """
        Given a marking and an enabled transition, computes the next marking.
        Returns a new marking tuple.
        """
        # Convert tuple to a mutable list
        new_marking_list = list(marking_tuple)
        
        # 1. Remove tokens from input places
        for in_place in transition.inputs:
            index = self.place_id_to_index[in_place.id]
            new_marking_list[index] = 0
            
        # 2. Add tokens to output places
        # (We assume 1-safe, so we just set to 1)
        for out_place in transition.outputs:
            index = self.place_id_to_index[out_place.id]
            new_marking_list[index] = 1
            
        return tuple(new_marking_list)

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
    # --- THIS IS THE NEW LINE YOU MUST ADD ---
    net.finalize_structure()
    # ----------------------------------------
    return net

def compute_explicit_reachability(petri_net):
    """
    Performs a BFS to find all reachable markings.
    Returns a set() of all reachable marking tuples.
    """
    print("\n--- Starting Task 2: Explicit Reachability Analysis ---")
    start_time = time.time()

    # The 'visited' set stores all markings we have ever seen.
    visited_markings = set()
    
    # The 'queue' stores markings we need to explore.
    # We use a deque for an efficient queue.
    queue = collections.deque()

    # 1. Get the starting state
    start_marking = petri_net.get_initial_marking_tuple()
    
    # 2. Add the starting state to the queue and visited set
    queue.append(start_marking)
    visited_markings.add(start_marking)

    # 3. Loop while the queue is not empty
    while queue:
        # Get the next marking to explore
        current_marking = queue.popleft()

        # Find all transitions that can fire from this state
        enabled_transitions = petri_net.get_enabled_transitions(current_marking)

        # For each possible move...
        for trans in enabled_transitions:
            # ...calculate the new state (marking)
            next_marking = petri_net.fire_transition(current_marking, trans)

            # Check if we have *ever* seen this new state before
            if next_marking not in visited_markings:
                # If it's brand new:
                # 1. Add it to our 'visited' list
                visited_markings.add(next_marking)
                # 2. Add it to the queue to explore later
                queue.append(next_marking)

    # 4. When the loop finishes, the queue is empty,
    #    and 'visited_markings' contains every possible state.
    end_time = time.time()
    
    print(f"Explicit analysis complete.")
    print(f"  Total reachable markings found: {len(visited_markings)}")
    print(f"  Time taken: {end_time - start_time:.6f} seconds")
    
    return visited_markings



#
# --- (Your __main__ block from Task 1) ---
#
if __name__ == "__main__":
    
    # (Dummy PNML file content from Task 1)
    dummy_pnml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <pnml xmlns="http://www.pnml.org/version-2009/grammar/pnml">
      <net id="net1" type="http://www.pnml.org/version-2009/grammar/ptnet">
        <page id="page1">
          <place id="p1"><initialMarking><text>1</text></initialMarking></place>
          <place id="p2"><initialMarking><text>0</text></initialMarking></place>
          <transition id="t1"></transition>
          <arc id="a1" source="p1" target="t1"/>
          <arc id="a2" source="t1" target="p2"/>
        </page>
      </net>
    </pnml>
    """
    
    with open("test_net.pnml", "w") as f:
        f.write(dummy_pnml_content)

    # --- Task 1 ---
    petri_net = parse_pnml("test_net.pnml")

    if petri_net:
        # --- Task 2 ---
        reachable_markings = compute_explicit_reachability(petri_net)
        
        # Optional: Print all the markings you found
        print("\nAll reachable markings (Place order: p1, p2):")
        for marking in sorted(list(reachable_markings)):
            print(f"  {marking}")
