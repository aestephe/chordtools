import math
import sys
import abjad
import lxml.etree
from pyalex.chord import *
from pyalex.utilities import *
sys.path.append(".")

def sort_and_trim_chords(chords, number):
	return sorted(chords, key = lambda c: (-1 * c.get_midi_intervals().count(3), c.total_span(), c.interval_variety()))[:number]

def build_spectra_from_all_poss_common_tones(previous_chord, overtone_classes, lower_bound, upper_bound, pitch_quantization):
	new_chords = []
	# each pitch from the previous chord which is a harmonic tone could be a common tone with a new chord
	for p in (p for p in previous_chord.pitches if p.is_harmonic_tone):
		partial_freq = Utilities.mtof(p.midi_number)
		# in the new chord, this common tone could be of any partial number selected from the overtone classes list
		# for example: if 7 and 11 are in the overtone classes list, this tone could be the 7th or 11th partial in the new chord
		for partial_number in (pn for pn in overtone_classes if pn > 1):
			should_continue = True
			partial_number_multiplier = 0
			while should_continue:
				# ... its partial number could also be an integer multiple of any of these overtone classes
				# for example: it could be not only the 7th, or 11th, etc. partial but also the 14th, or 22nd, etc.
				partial_number_multiplier += 1
				new_fund_freq = partial_freq/(partial_number * partial_number_multiplier)
				new_fund_midi = 12 * math.log(float(new_fund_freq/440), 2) + 69
				new_fund_midi = round(new_fund_midi * (1/pitch_quantization)) / (1/pitch_quantization)
				if new_fund_midi >= lower_bound:
					# don't bother building the chord if it duplicates the fundamental of the previous chord
					if not Utilities.are_pcs_equal(new_fund_midi, previous_chord.fundamental.midi_number):
						new_fund_pitch = Pitch(new_fund_midi, 1)
						chord = Chord.from_fund_and_overtone_classes(new_fund_pitch, overtone_classes, 
																	lower_bound, upper_bound, pitch_quantization)
						# HACK to prevent duplicates in the list... need to figure out why this is happening
						if not str(chord) in (str(x) for x in new_chords):
							new_chords.append(chord)
				else:
					should_continue = False	
	return new_chords

if len(sys.argv) < 2:
	raise ValueError("XML parameter filepath required")
	
xml_root = lxml.etree.parse(str(sys.argv[1]))
	
# parse parameters
previous_chord = Chord.from_string(Utilities.get_param_val(xml_root, "previous_chord"))
overtone_classes = Utilities.string_to_list_of_float(
					Utilities.get_param_val(xml_root, "overtone_classes"))
pitch_quantization = float(Utilities.get_param_val(xml_root, "pitch_quantization"))
lower_bound = float(Utilities.get_param_val(xml_root, "lower_bound"))
upper_bound = float(Utilities.get_param_val(xml_root, "upper_bound"))
force_fund_register = bool(int(Utilities.get_param_val(xml_root, "force_fund_register")))
nct_overtone_classes = Utilities.string_to_list_of_float(
					Utilities.get_param_val(xml_root, "nct_overtone_classes"))
nct_lower_bound = float(Utilities.get_param_val(xml_root, "nct_lower_bound"))
nct_upper_bound = float(Utilities.get_param_val(xml_root, "nct_upper_bound"))
mandatory_pitches = Pitch.array_from_midi(Utilities.string_to_list_of_float(
					Utilities.get_param_val(xml_root, "mandatory_pitches")))
banned_pitches = Pitch.array_from_midi(Utilities.string_to_list_of_float(
					Utilities.get_param_val(xml_root, "banned_pitches")))
mandatory_intervals = Utilities.string_to_list_of_float(
					Utilities.get_param_val(xml_root, "mandatory_intervals"))
banned_intervals = Utilities.string_to_list_of_float(
					Utilities.get_param_val(xml_root, "banned_intervals"))
oclass_fit_in_octave = Utilities.string_to_list_of_float(
						Utilities.get_param_val(xml_root, "oclass_fit_in_octave"))
min_number_common_tones = int(Utilities.get_param_val(xml_root, "min_number_common_tones"))
max_number_common_tones = int(Utilities.get_param_val(xml_root, "max_number_common_tones"))
count_ncts_as_common_tones = bool(int(Utilities.get_param_val(xml_root, "count_ncts_as_common_tones")))
max_number_results = int(Utilities.get_param_val(xml_root, "max_number_results"))
common_tone_highlight_color = Utilities.get_param_val(xml_root, "common_tone_highlight_color")
nct_notehead_style = Utilities.get_param_val(xml_root, "nct_notehead_style")

if min_number_common_tones < 1:
	raise ValueError("the minimum desired number of common tones must be at least 1")

print("")
print("Generating raw spectra from all possible common tones...")
new_chords = build_spectra_from_all_poss_common_tones(previous_chord, overtone_classes, lower_bound, upper_bound, pitch_quantization)
print(str(len(new_chords)) + " spectra generated")
#for c in new_chords:
#	print(c.to_string())

if len(nct_overtone_classes) > 0:
	print("")
	print("Adding all possible non-chord tones...")
	for c in new_chords:
		c.add_ncts_from_overtone_classes(nct_overtone_classes, nct_lower_bound, nct_upper_bound, pitch_quantization)
	
print("")
print("Finding voicings...")
new_chords_exploded = []
i = 0
for c in new_chords:
	i += 1
	c_list = c.get_unique_pc_voicings(force_fund_register)
	new_chords_exploded.extend(c_list)
	print("--> Spectrum " + str(i) + ": " + str(len(c_list)) + " voicings added")
print(str(len(new_chords_exploded)) + " voicings found total")

print("")
print("Applying filtering conditions...")
filtered_chords = []
unique_fundamentals = {}
for c in new_chords_exploded:

	should_include = True
	
	# All requested overtone classes should be represented
	if len([p for p in c.pitches if p.is_harmonic_tone]) < len(overtone_classes):
		should_include = False
	
	# All mandatory pitches must be present
	if len(mandatory_pitches) > 0 and c.contains_all_pitches(mandatory_pitches) == False:
		should_include = False
	
	# No banned pitches should be present
	if len(banned_pitches) > 0 and c.contains_any_pitches(banned_pitches):
		should_include = False
	
	# All mandatory intervals must be present
	if len(mandatory_intervals) > 0 and c.contains_all_intervals(mandatory_intervals) == False:
		should_include = False
		
	# No banned intervals should be present
	if len(banned_intervals) > 0 and  c.contains_any_intervals(banned_intervals):
		should_include = False

	# Enforce overtone classes which need to be voiced within an octave of each other
	if len(oclass_fit_in_octave) > 0: 
		if (max([p.midi_number for p in c.pitches if p.overtone_class in oclass_fit_in_octave]) -
			min([p.midi_number for p in c.pitches if p.overtone_class in oclass_fit_in_octave]) > 12):
			should_include = False
	
	# Number of common tones should be within the min/max
	if len(c.get_common_tones(previous_chord, count_ncts_as_common_tones)) < min_number_common_tones:
		should_include = False
	if len(c.get_common_tones(previous_chord, count_ncts_as_common_tones)) > max_number_common_tones:
		should_include = False

	if should_include:
		filtered_chords.append(c)
		if c.fundamental.midi_number in unique_fundamentals:
			unique_fundamentals[c.fundamental.midi_number] += 1
		else:
			unique_fundamentals[c.fundamental.midi_number] = 1

print(str(len(filtered_chords)) + " chords remain")

print("")
print("Sampling unique fundamentals; sorting and trimming chords...")
sorted_chords = []
chords_added = 0
trim_divisor = len(filtered_chords)/max_number_results
if trim_divisor < 1:
	trim_divisor = 1
unique_fundamentals_trimmed = {}
for f in sorted(unique_fundamentals):
	chords_for_this_fund = [c for c in filtered_chords if c.fundamental.midi_number == f]
	# number of chords which have this fundamental divided by the trim divisor
	# ensures proportional representation of fundamentals in the trimmed list
	number_chords_to_add = round(unique_fundamentals[f]/trim_divisor)
	chords_added += number_chords_to_add
	if chords_added > max_number_results:
		number_chords_to_add -= 1 # to prevent rounding errors
	sorted_chords.extend(sort_and_trim_chords(chords_for_this_fund, number_chords_to_add))
	unique_fundamentals_trimmed[f] = number_chords_to_add

#print("")
#print("Sorting and trimming list...")
#sorted_chords = sort_and_trim_chords(filtered_chords, max_number_results)
#sorted_chords = sorted(sorted_chords, key = lambda c: (c.fundamental.midi_number))

print(str(len(sorted_chords)) + " chords remain")

chords_remain = False
if len(sorted_chords) > 0:
	chords_remain = True

print("")
print("Chords to be notated:")
for i in range(0, len(sorted_chords)):
	print(str(i + 2) + '\t' + str(sorted_chords[i]))
	
print("")
print("Unique fundamentals found:")
for f in list(sorted(unique_fundamentals)):
	print(str(f) + '\t' + '(' + str(Utilities.get_anglophone_pitch_class(f)) + ')' + '\t' + str(unique_fundamentals[f])
			+ '\t' + str(unique_fundamentals_trimmed[f]) + " after trimming")
	

print("")
print("Notating...")
lower_staff_components = []
upper_staff_components = []

# append the previous chord, with all pitches highlighted
lower_previous_pitches = [p for p in previous_chord.pitches if p.midi_number < 60]
lower_previous_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
if len(lower_previous_pitches) > 0:
	for i in range(0, len(lower_previous_pitches)):
		lower_previous_abjad_chord.note_heads.extend([lower_previous_pitches[i].midi_number - 60])
		abjad.tweak(lower_previous_abjad_chord.note_heads[i]).color = common_tone_highlight_color
		if lower_previous_pitches[i].is_harmonic_tone == False:
			abjad.tweak(lower_previous_abjad_chord.note_heads[i]).style = nct_notehead_style
	lower_staff_components.append(lower_previous_abjad_chord)
else:
	lower_staff_components.append(abjad.Rest(abjad.Duration(1, 1)))
upper_previous_pitches = [p for p in previous_chord.pitches if p.midi_number >= 60]
upper_previous_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
if len(upper_previous_pitches) > 0:
	for i in range(0, len(upper_previous_pitches)):
		upper_previous_abjad_chord.note_heads.extend([upper_previous_pitches[i].midi_number - 60])
		abjad.tweak(upper_previous_abjad_chord.note_heads[i]).color = common_tone_highlight_color
		if upper_previous_pitches[i].is_harmonic_tone == False:
			abjad.tweak(upper_previous_abjad_chord.note_heads[i]).style = nct_notehead_style
	upper_staff_components.append(upper_previous_abjad_chord)
else:
	upper_staff_components.append(abjad.Rest(abjad.Duration(1, 1)))

# now append each of the new chords - common tones with the previous chord are highlighted
for c in sorted_chords:

	lower_pitches = [p for p in c.pitches if p.midi_number < 60]
	lower_common_tones = [ct for ct in c.get_common_tones(previous_chord, count_ncts_as_common_tones) if ct.midi_number < 60]
	lower_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
	if len(lower_pitches) > 0:
		for i in range(0, len(lower_pitches)):
			lower_abjad_chord.note_heads.extend([lower_pitches[i].midi_number - 60])
			if lower_pitches[i] in lower_common_tones:
				abjad.tweak(lower_abjad_chord.note_heads[i]).color = common_tone_highlight_color
			if lower_pitches[i].is_harmonic_tone == False:
				abjad.tweak(lower_abjad_chord.note_heads[i]).style = nct_notehead_style
		lower_staff_components.append(lower_abjad_chord)
	else:
		lower_staff_components.append(abjad.Rest(abjad.Duration(1, 1)))		
	
	upper_pitches = [p for p in c.pitches if p.midi_number >= 60]
	upper_common_tones = [ct for ct in c.get_common_tones(previous_chord, count_ncts_as_common_tones) if ct.midi_number >= 60]
	upper_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
	if len(upper_pitches) > 0:
		for i in range(0, len(upper_pitches)):
			upper_abjad_chord.note_heads.extend([upper_pitches[i].midi_number - 60])
			if upper_pitches[i] in upper_common_tones:
				abjad.tweak(upper_abjad_chord.note_heads[i]).color = common_tone_highlight_color
			if upper_pitches[i].is_harmonic_tone == False:
				abjad.tweak(upper_abjad_chord.note_heads[i]).style = nct_notehead_style
		upper_staff_components.append(upper_abjad_chord)
	else:
		upper_staff_components.append(abjad.Rest(abjad.Duration(1, 1)))	
		
lower_staff = abjad.Staff(lower_staff_components)
upper_staff = abjad.Staff(upper_staff_components)

if len(lower_staff_components) > 0:
	leaf = abjad.get.leaf(lower_staff, 0)
	abjad.attach(abjad.Clef('bass'), leaf)

piano_staff = abjad.StaffGroup([], lilypond_type='PianoStaff')
piano_staff.append(upper_staff)
piano_staff.append(lower_staff)

if chords_remain:
	abjad.show(piano_staff)
else:
	print("Nothing to notate!")
	pass # don't bother generating a pdf - no chords were found 