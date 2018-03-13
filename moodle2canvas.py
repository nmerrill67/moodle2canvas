#!/usr/bin/env python3
import csv
import sys
from time import strftime
from re import match
import numpy as np

def moodle2canvas(moodle_fl="moodle.csv", canvas_fl="grades.csv", lab_sec_fl="my_sections.csv", grade_col_ind=11, responses_fl="responses.csv", partner_col_ind=12, check_groups=False):
	'''
	moodle2canvas for partner/group assignements (i.e. labs)
	Args:

	moodle_fl (default="moodle.csv") - str: the input grades file in moodle format found on the quiz server under Results -> Grades. This can be all sections appended together

	canvas_fl (default="grades.csv") - str: the input grades file in canvas format. This shouold contain all grades from all students in that particular section
	
	lab_sec_fl (default="my_sections.csv") - str: a csv containing only YOUR lab sections with tho columns set up as: ID, Email. Note: this assumes that the first line starts with actual data, and not a column headear (very important)

	grade_col_ind (default=11) - int: the column index of 'Grade/10.00'. Please change this value if it appears differently on your moodle csv

	responses_fl (default=responsess.csv) - str: The csv response file downloaded from Moodle. Can be all sections appended together
	
	partner_col_ind - the column index of the partner question in responses_fl

	Output:

	</path/to/canvas_fl_name>_updated_<date>_with_<Lab/Quiz name>.csv - file: This is the file of <canvas_fl> merged with the new quiz grades from <moodle_fl> in canvas format--ready to upload after fixing the Manual entries
	''' 
	ids_by_username = {} # access ids by username, taken from the lab sections csv
	username_by_id = {}
	print('\n\nReading students in your lab section ...')
	with open(lab_sec_fl) as fin:
		for line in fin:
			line_split = line.split(',')
			ids_by_username[line_split[1].split('@')[0]] = line_split[0] 
			username_by_id[line_split[0]] = line_split[1].split('@')[0]
	# Now that we have all the UDIDs based on udel username, we can accurately tell one student from another, and only process the grades for our lab sections 
	# Moodle accurately provides the udel username, but not student name or UDID
	# Canvas provides the udel username, but not the UDID, so this mapping is necessary	

	

	all_grades={}
	print('Reading Moodle submissions ...')
	max_moodle_grade = -1
	with open(moodle_fl) as fin:
		for line in fin:
			if 'Grade' in line: # first line. Get max moodle grade
				max_moodle_grade = float(line.strip().lower().split(',')[grade_col_ind].split('/')[1])	
			else:
				line_split=line.strip().lower().split(',')
				udel_username = line_split[3]
				if udel_username in ids_by_username.keys():
					grade = line_split[grade_col_ind].strip()
					if grade == '-':# Check if the quiz server screwed up and didnt submit automatically, but if they actually have nothing give them a zero
						print(udel_username,",", ids_by_username[udel_username], "started the quiz/lab, but Moodle did not submit it automatically. Calculating their grade now...")
						grade_float = 0.0
						for q_grade in line_split[(grade_col_ind+1):]:
							if q_grade.strip() != '-':
								grade_float += float(q_grade.strip())
						grade = str(grade_float)
						print(udel_username,"'s grade is now ", grade)
					if ids_by_username[udel_username] in all_grades.keys(): # check for multiple submissions. Want the max
						if float(all_grades[ids_by_username[udel_username]]) < float(grade):	
							all_grades[ids_by_username[udel_username]] = grade
					else:
						all_grades[ids_by_username[udel_username]] = grade
	if max_moodle_grade < 0:
		raise ValueError("Max Moodle Grade not found! Ensure that \"Grade/<max grade>\" is in the column header of column " + grade_col_ind + ". If the column index is wrong, please pass the correct one to this function") 

	if check_groups:
		print("Cross-checking groups with individual submissions...")
		groups = [] # nested list of groups
		with open(responses_fl) as fin:
			for line in fin:
				line_split = line.strip().split(',')
				if not line_split[0].strip() == "Surname":
					group = [line_split[3].strip()] # Username of submitter
					partners = line_split[partner_col_ind].strip().strip('\"').split(';')
					for partner in partners:
						if len(partner.strip()) == 9: # Make sure its not random text
							if partner.strip() in username_by_id.keys():
								group.append(username_by_id[partner.strip()]) # Append multiple partners if there are any
					groups.append(group)
		groups = np.array(groups) # Do this so we can use logical indexing later

		missing_students_log_fl_name = canvas_fl.split('.')[0] + "_missing_students.log"
		log_fl = open(missing_students_log_fl_name, 'w')
		msg = "\n\nthe following students are in your lab sections, but were not found in any group listed in " + responses_fl + ", and they do not have an individual moodle submission. they will receive a zero for now.\nUDID,    Username\n"
		print(msg)
		log_fl.write(msg)
		for uname in ids_by_username.keys():
			is_in_group_i = np.array([uname in group for group in groups])
			has_submitted = ids_by_username[uname] in all_grades.keys()
			if not any(is_in_group_i) and not has_submitted:
				log_fl.write(str(ids_by_username[uname]) + ", " + str(uname) + "\n")
				print(str(ids_by_username[uname]) + ", " + str(uname))
				all_grades[ids_by_username[uname]] = '0.0'
			elif any(is_in_group_i): # Student found, loop through the groups and assign their grades
				# Find max group submission grade
				students_groups = groups[is_in_group_i] # May return multiple groups/single submissions, we want the max for each student (i.e. if they submitted alone after a group member bailed)
				max_group_grade = '0.0'
				for group in students_groups:
					for group_member_uname in group:
						if group_member_uname in ids_by_username.keys() and ids_by_username[group_member_uname] in all_grades.keys():
							if float(all_grades[ids_by_username[group_member_uname]]) > float(max_group_grade):
							
								max_group_grade = all_grades[ids_by_username[group_member_uname]]
				all_grades[ids_by_username[uname]] = max_group_grade	
			# Else they submitted individually
	else: # single person activity, dont look for groups
		msg = "\n\nThe following students are in your lab sections, but have no Moodle submission. They will receive a 0 for now.\nUDID,    Username\n"
		missing_students_log_fl_name = canvas_fl.split('.')[0] + "_missing_students.log"
		log_fl = open(missing_students_log_fl_name, 'w')
		print(msg)
		log_fl.write(msg)
		for uname in ids_by_username.keys():
			if ids_by_username[uname] not in all_grades.keys():
				print(str(ids_by_username[uname]) + ", " + str(uname))
				all_grades[ids_by_username[uname]] = '0.0'

	scoreFIN = csv.reader(open(canvas_fl)) 
	line1 = next(scoreFIN)
	poss_cols_to_edit = []
	for col in line1:
		if match("Quiz [0-9]", col)!=None or match("Lab [0-9]", col)!=None:
			poss_cols_to_edit.append(col)

	correct = False
	col_to_edit = -1
	while not correct:
		field_to_edit = str(input("\nPlease type the field you wish to edit (exactly).\nChoices are: " + str(poss_cols_to_edit[:]) + "\nEntry: ")) # This script is only for Quizzes and labs, so only show those cols
		try:
			col_to_edit = line1.index(field_to_edit)
			print("You have chosen to edit " + field_to_edit)
			correct = True
		except:
			print("\nIncorrect entry. Please make sure there are no typos. You can always copy and paste")


	print('Reading Canvas file ...') 
	print("\n\nThe following students are in your canvas lecture section, but were not found in " + lab_sec_fl + ". Please ignore if they are a TA or a test student")
	print("UDID,    Student Name")
	log_fl.write("\n\nThe following students are in your canvas lecture section, but were not found in " + lab_sec_fl + ". Please ignore if they are a TA or a test student.\nUDID,    Student Name")
	new_canvas_csv = [line1] # The matrix to write to the new csv file	
	pts_poss_row = False 
	while not pts_poss_row: # Find the row with the max number of canvas points
		line = next(scoreFIN) # go to next row
		new_canvas_csv.append(line)
		if "Points Possible" in line[0].strip():
			pts_poss_row = True

	max_canvas_grade = float(line[col_to_edit].strip()) # Adjust the grade according to the max grade ratio
	mult = max_canvas_grade / max_moodle_grade
	for row in scoreFIN:
		udid = row[2].strip() # extract udid from canvas file line
		if udid in all_grades.keys(): # first check if in our lab section,  then check is in this current canvas section (because we have three different canvas pages for three different sections of the same class for some reason)
			row[col_to_edit] = str(float(all_grades[udid])*mult) # Edit the new grade in the correct place
		else:
			print(str(udid) + ", " + row[0].strip())
			log_fl.write(str(udid) + ", " + row[0].strip() + "\n")
		new_canvas_csv.append(row)

	# Now write the new file to $PWD as "<old canvas file name>_update_<date>.csv"
	new_canvas_fl = canvas_fl.split('.')[0] + '_updated_' + strftime("%d-%m-%Y_%I%M%S") + '_with_' + field_to_edit.split('(')[0] + '.csv'
	new_canvas_writer = csv.writer(open(new_canvas_fl, 'w'), delimiter=',')
	for row in new_canvas_csv:
		new_canvas_writer.writerow(row)

	print("\nUpdated canvas csv written to: " + new_canvas_fl + "\n\n")
	print("All missing students written to: " + missing_students_log_fl_name)
# Main (gets run if you run this as a script and not as a library call)
if __name__ == '__main__':
	'''
	Run from the terminal as: 
	$ python moodle2canvas_style.py -mf <moodle file name>
	OR
	$ ./moodle2canvas_style.py -mf <moodle file name>
	if on linux (must have /usr/bin/env 
	'''

	from argparse import ArgumentParser
	parser = ArgumentParser()
	subparsers = parser.add_subparsers(dest='subparser') 

	# Default vals
	default_moodle_fl = 'moodle.csv'
	default_canvas_fl = 'grades.csv'
	default_lab_sec_fl = 'my_sections.csv'
	default_grade_col_ind = 11
	default_response_fl = 'responses.csv'

	single_parser = subparsers.add_parser('single', help='Use this for single-person assignments (i.e. Quizzes). Use `./moodle2canvas.py single -h` for specific arguments.')
	group_parser = subparsers.add_parser('group', help='Use this for group assignments (i.e. Labs). Use `./moodle2canvas group -h for specific arguments.')

	# Both subparsers share these args
	for subparser in [single_parser, group_parser]:	
		subparser.add_argument('--moodle-fl','-m', dest='moodle_fl', nargs='?', default=default_moodle_fl, help='The input file in moodle format for the results of a quiz. Default is: ' + default_moodle_fl)
		subparser.add_argument('--canvas-fl','-c', dest='canvas_fl', nargs='?', default=default_canvas_fl, help='The input file of all grades in canvas format. This file will not be overwritten. Default is: ' + default_canvas_fl)

		subparser.add_argument('--lab-sec-fl','-l', dest='lab_sec_fl', nargs='?', default=default_lab_sec_fl, help='The input csv file of all your lab sections with only two columns of \'ID, Email\' (with no column headers). Default is: ' + default_lab_sec_fl)

		subparser.add_argument('--grade-col-ind','-i', dest='grade_col_ind', nargs='?', default=default_grade_col_ind, help="The column index of 'Grade/<max grade>'. Please change this value if it appears differently on your moodle csv. Default is: " + str(default_grade_col_ind), type=int)

		subparser.add_argument('--response-fl', '-r', dest='response_fl', nargs='?', default=default_response_fl, help='The repsonse file downloaded from Moodle WITH EVERY COLUMN AFTER QUESTION 1 REMOVED. Can have multiple sections appended. Default is: ' + default_response_fl) 

	args = parser.parse_args()
	main_check_groups = False
	if args.subparser == 'group':
		main_check_groups = True	
	moodle2canvas(args.moodle_fl, args.canvas_fl, args.lab_sec_fl, args.grade_col_ind, args.response_fl, check_groups=main_check_groups)


