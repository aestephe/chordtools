import math
import sys
import abjad
import lxml.etree
from pyalex.chord import *
from pyalex.utilities import *
from pyalex.pitch import *

def sort_and_trim_chords(chords, number):
	return sorted(chords, key = lambda c: (c.total_span(), c.interval_variety()))[:number]

if len(sys.argv) < 2:
	raise ValueError("XML parameter filepath required")
	
xml_root = lxml.etree.parse(str(sys.argv[1]))
	
# parse parameters
fund_pitch = Pitch(float(Utilities.get_param_val(xml_root, "fund_pitch")))
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
max_number_results = int(Utilities.get_param_val(xml_root, "max_number_results"))
nct_notehead_style = Utilities.get_param_val(xml_root, "nct_notehead_style")

print("")
print("Generating raw spectrum...")
spectrum = Chord.from_fund_and_overtone_classes(
					fund_pitch, 
					overtone_classes, 
					lower_bound, 
					upper_bound,
					pitch_quantization)
print(spectrum.get_midi_numbers())

print("")
print("Retrieving pitch-class pointers...")
for pointer in spectrum.pointers:
	print(str(pointer.pitch_class_number) + '\t' + str(pointer.indices))
	
if len(nct_overtone_classes) > 0:
	print("")
	print("Adding all possible non-chord tones...")
	spectrum.add_ncts_from_overtone_classes(nct_overtone_classes, nct_lower_bound, nct_upper_bound, pitch_quantization)
	
	print(spectrum.get_midi_numbers())
	print("")
	print("Retrieving updated pitch-class pointers...")
	for pointer in spectrum.pointers:
		print(str(pointer.pitch_class_number) + '\t' + str(pointer.indices))
	
print("")
print("Generating voicings...")
chords = spectrum.get_unique_pc_voicings()
print(str(len(chords)) + " chords found")

print("")
print("Applying filtering conditions...")
filtered_chords = []
for c in chords:

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

	if should_include:
		filtered_chords.append(c)
		
print(str(len(filtered_chords)) + " chords remain")

print("")
print("Sorting and trimming list...")
sorted_chords = sort_and_trim_chords(filtered_chords, max_number_results)

print(str(len(sorted_chords)) + " chords remain")

chords_remain = False
if len(sorted_chords) > 0:
	chords_remain = True

print("")
print("Chords to be notated:")
for i in range(0, len(sorted_chords)):
	#print(str(i + 1) + '\t' + str(sorted_chords[i].get_midi_numbers()))
		# + ' ' + str(round(midi_chords_sorted[i].average_spacing(), 2))
		# + ' ' + str(midi_chords_sorted[i].median_spacing())
		# + ' ' + str(midi_chords_sorted[i].spacing_variety()))
	print(str(i + 1) + '\t' + str(sorted_chords[i]))

print("")
print("Notating...")
lower_staff_components = []
upper_staff_components = []

for c in sorted_chords:

	lower_pitches = [p for p in c.pitches if p.midi_number < 60]
	lower_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
	if len(lower_pitches) > 0:
		for i in range(0, len(lower_pitches)):
			lower_abjad_chord.note_heads.extend([lower_pitches[i].midi_number - 60])
			if lower_pitches[i].is_harmonic_tone == False:
				abjad.tweak(lower_abjad_chord.note_heads[i]).style = nct_notehead_style
		lower_staff_components.append(lower_abjad_chord)
	else:
		lower_staff_components.append(abjad.Rest(abjad.Duration(1, 1)))		
	
	upper_pitches = [p for p in c.pitches if p.midi_number >= 60]
	upper_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
	if len(upper_pitches) > 0:
		for i in range(0, len(upper_pitches)):
			upper_abjad_chord.note_heads.extend([upper_pitches[i].midi_number - 60])
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

