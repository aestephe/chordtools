import sys
import abjad
from pyalex.chord import *

if len(sys.argv) < 3:
	raise ValueError("Required parameters: notebook file path, mode")

file_path = sys.argv[1]
mode_text = sys.argv[2]

if not file_path.endswith(".txt"):
	raise ValueError("File path must be a txt file")

if mode_text.lower() == "read":

	with open(file_path, 'r') as file:

		lower_staff_components = []
		upper_staff_components = []

		lines = file.readlines()

		if len(lines) > 0:

			for line in lines:

				c = Chord.from_string(line)

				lower_pitches = [p for p in c.pitches if p.midi_number < 60]
				lower_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
				if len(lower_pitches) > 0:
					for i in range(0, len(lower_pitches)):
						lower_abjad_chord.note_heads.extend([lower_pitches[i].midi_number - 60])
						if lower_pitches[i].is_harmonic_tone == False:
							abjad.tweak(lower_abjad_chord.note_heads[i]).style = 'harmonic'
					lower_staff_components.append(lower_abjad_chord)
				else:
					lower_staff_components.append(abjad.Rest(abjad.Duration(1, 1)))		
				
				upper_pitches = [p for p in c.pitches if p.midi_number >= 60]
				upper_abjad_chord = abjad.Chord([], abjad.Duration(1, 1))
				if len(upper_pitches) > 0:
					for i in range(0, len(upper_pitches)):
						upper_abjad_chord.note_heads.extend([upper_pitches[i].midi_number - 60])
						if upper_pitches[i].is_harmonic_tone == False:
							abjad.tweak(upper_abjad_chord.note_heads[i]).style = 'harmonic'
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

			abjad.show(piano_staff)

		else:

			print("Nothing to notate!")

elif mode_text.lower() == "write":

	if len(sys.argv) < 4:
		raise ValueError("No string provided to write to file")

	chord_string = sys.argv[3]

	# make sure the chord string is of valid format
	try:
		c = Chord.from_string(chord_string)
	except:
		raise ValueError("Chord string not of valid format")


	with open(file_path, 'a') as file:
		file.write(chord_string + '\n')

elif mode_text.lower() == "clear":

	#with open(file_path, 'r+') as file:
	#	file.truncate(0)
	print("Did not clear - manually delete from file instead")

else:

	raise ValueError("Unexpected mode value - should be read, write, or clear")
