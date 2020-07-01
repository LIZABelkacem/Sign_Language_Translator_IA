#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
AKKAL Aghilas
BELKACEM Liza
'''

import Leap, sys, os, thread, time, random, math, threading, pickle, tkMessageBox, utils
from time import sleep
from Tkinter import *


class SetNameDialog:
	'''
	Fenetre pour la création d'un nouveau signe
	'''
	def __init__(self, parent):
		top = self.top = Toplevel(parent)
		top.wm_title("Nouveau signe")

		# Affiche la fenetre de création du signe
		Label(top, text='Mot / Lettre:').grid(row=0, pady=5)
		self.myEntryBox = Entry(top)
		self.myEntryBox.grid(row=0, column=1, columnspan=3)

		# Affiche le type du signe
		Label(top, text='Type:').grid(row=1, column=0, pady=5)
		self.radioButtonValue = IntVar()
		Radiobutton(top, text="Gesture", variable=self.radioButtonValue, value=0).grid(row=1, column=1, pady=5)
		Radiobutton(top, text="Fixed", variable=self.radioButtonValue, value=1).grid(row=1, column=2)

		# Affiche le button OK pour retourner a la fenetre principale
		Button(top, text='OK', command=self.send).grid(row=3, column=1, columnspan=2, pady=2)
		self.value = ''


	def send(self):
		'''
		Enregistrer les valeurs une fois la fenetre fermée
		'''
		if self.radioButtonValue.get() == 0:
			self.signType = 'Gesture'
		else:
			self.signType = 'Fixed'

		self.value = self.myEntryBox.get()
		self.top.destroy()


class GUI:
	'''
	fenetre principale de l'application
	'''
	def __init__(self, master):
		'''
		Initiation de la fenetre, des variables et des elements GUI
		'''


		self.master = master
		self.master.protocol('WM_DELETE_WINDOW', self.close)
		self.dataset = []
		self.vectorBuffer = []

		# Charge la dataset si existante, sinon commence avec une nouvelle dataset vide
		if os.path.exists('dataset.p'):
			with open('dataset.p', 'rb') as f:
				try:
					self.dataset = pickle.load(f)
					# validation des objets dans la dataset
					for sign in self.dataset:
						if not isinstance(sign, utils.Sign):
							self.master.update()
							tkMessageBox.showwarning('', \
								"un object non-signe a été trouvé dans 'dataset.p'\n" + \
								" Création d'une nouveau dataset vide.")
							self.master.update()
							self.dataset = []
							break
				except Exception:
					self.master.update()
					tkMessageBox.showwarning('', 'Erruer lors de la lecture du fichier.\n' + \
						"Création d'une nouveau dataset vide.")
					self.dataset = []

		# Assigner le controlleur Leap + temps d'attente
		self.controller = Leap.Controller()
		sleep(0.01)

		# Liste défilable des signes
		self.signsScrollbar = Scrollbar(master)
		self.signsList = Listbox(master, yscrollcommand=self.signsScrollbar.set, exportselection=0)
		self.signsList.grid(row=0, rowspan=5, column=0, columnspan=2)
		self.signsList.bind('<<ListboxSelect>>', self.signsListBoxSelect)
		self.signsScrollbar.config(command=self.signsList.yview)
		self.signsScrollbar.grid(row=0, column=2, rowspan=5, sticky=N+S)

		# Liste défilable des signes des captures
		self.samplesScrollbar = Scrollbar(master)
		self.samplesList = Listbox(master, yscrollcommand=self.samplesScrollbar.set)
		self.samplesList.grid(row=0, rowspan=5, column=3, columnspan=2)
		self.samplesScrollbar.config(command=self.samplesList.yview)
		self.samplesScrollbar.grid(row=0, column=5, rowspan=5, sticky=N+S)

		# Boutons pour controller les signes
		self.deleteSign = Button(master, text="Supprimer", command=self.deleteSign)
		self.deleteSign.grid(row=6, column=0)
		self.createSignButton = Button(master, text="Nouveau", command=self.createSign)
		self.createSignButton.grid(row=6, column=1)

		# Boutons pour controller les captures
		self.deleteSampleButton = Button(master, text="Supprimer dernier", command=self.deleteSample)
		self.deleteSampleButton.grid(row=6, column=3)
		self.recordButton = Button(master, text="Enregistrer")
		self.recordButton.bind("<Button-1>", self.startRecording)
		self.recordButton.bind("<ButtonRelease-1>", self.stopRecording)
		self.recordButton.grid(row=6, column=4)

		self.isRecording = False

		# Initiation de la premiere liste
		self.updateSignsList()

		# pas de signe actuellement selectioné
		self.currentSign = None


	def updateSignsList(self):
		'''
		Met a jour la liste de signes
		et en ordre alphabetique
		'''
		self.signsList.delete(0, END)
		self.dataset = sorted(self.dataset, key=lambda x : x.value)
		for sign in self.dataset:
			self.signsList.insert(END, ' '+sign.value)


	def updateSamplesList(self):
		'''
		Met a jour la liste des captures
		depuis la dataset
		'''
		if self.currentSign != None:
			self.samplesList.delete(0, END)
			for i in range(len(self.currentSign.samples)):
				self.samplesList.insert(END, ' '+str(i+1))
			self.samplesList.yview(END)
		else:
			self.samplesList.delete(0, END)


	def startRecording(self, event):
		'''
		Commence l'enregistrement des capture dans un thread séparé
		si la leap est connectée et la main est visible
		'''
		self.vectorBuffer = []
		if self.controller.is_connected:
			if len(self.controller.frame().hands) != 0:
				if self.currentSign != None:
					self.isRecording = True
					thread = threading.Thread(target=self._record)
					thread.start()
				else:
					tkMessageBox.showwarning('','Pas de signe détécté')
			else:
				tkMessageBox.showwarning('','Pas de main en vue')
		else:
			tkMessageBox.showwarning('','Leap Motion non-détéctée')


	def _record(self):
		'''
		Enregistre en moyenne 100 frames dans un 'vectorBuffer'
		'''
		while self.isRecording:
			if len(self.controller.frame().hands) != 0:
				hand = self.controller.frame().hands[0]
				self.vectorBuffer.append(hand)
				sleep(0.01)
			else:
				self.isRecording = False
				tkMessageBox.showwarning('','Pas de main en vue')


	def stopRecording(self, event):
		'''
		Arrete l'enregistrement des frames, et convertit
		le buffer des frames vers un vecteur de la meme langeur
		selon le type ('gestuelle' ou 'fixé')
		'''
		if self.isRecording:
			value = self.currentSign
			 # arrete le thread d'enregistrement
			self.isRecording = False

			if self.currentSign.type == 'Fixed' and len(self.vectorBuffer):
				self.currentSign.samples.append(utils.vectorize(self.vectorBuffer, fixed=True))

			# On vérifie qu'on a au moins 10 frames pour créer la gestuelle
			elif len(self.vectorBuffer) >= 10:
				self.currentSign.samples.append((self.vectorBuffer))

			else:
				tkMessageBox.showwarning('', 'Peu de frames enregistré. réassayer')
				return

			if len(self.currentSign.samples) >= 2:
				if not utils.validateFeatures(self.currentSign.samples):
					tkMessageBox.showwarning('', \
						'Valeur null enregistré depuis le capteur. Supprimer les captures du signe actuel et réassayer')

			pickle.dump(self.dataset, open('dataset.p', 'wb'))
			self.updateSamplesList()


	def createSign(self):
		'''
		Créer un objet signe, son type
		et mettre à jour la liste des signes
		'''

		inputDialog = SetNameDialog(self.master)
		self.master.wait_window(inputDialog.top)

		# Vérifie que le nom du signe est unique et non null
		value = inputDialog.value
		if len(value) > 0 and sum([1 for x in self.dataset if x.value == value]) == 0:
			self.currentSign = utils.Sign(value, inputDialog.signType, [])
			self.dataset.append(self.currentSign)

		# Actualise la GUI
		self.updateSignsList()


	def deleteSign(self):
		'''
		Affiche confirmation de suppression
		'''
		selected = self.signsList.curselection()

		if len(selected) > 0:
			if tkMessageBox.askyesno("Supprimer", "Etes-vous sur de supprimer ce signe ?"):
				self.currentSign = None
				del self.dataset[selected[0]]
				self.updateSignsList()
				self.updateSamplesList()
		else:
			tkMessageBox.showwarning('','Pas de signe détécté')


	def deleteSample(self):
		'''
		Supprime la derniere capture enregistrée
		'''
		selected = len(self.currentSign.samples) - 1
		if selected >= 0:
			del self.currentSign.samples[selected]
			self.updateSamplesList()
		else:
			tkMessageBox.showwarning('','Pas de capture restante')


	def signsListBoxSelect(self, event):
		'''
		Suivre la selection de l'utilisateur dans la liste
		'''
		selected = event.widget.curselection()

		# affect le signe actuel à celui séléctioné dans la liste
		if len(selected) > 0:
			# s'assure que le signe séléctioné est un int
			self.currentSign = self.dataset[int(selected[0])]
		self.updateSamplesList()


	def close(self):
		'''
		Enregistre la dataset avant de fermer
		'''
		pickle.dump(self.dataset, open('dataset.p', 'wb'))
		self.master.destroy()


def main():
	'''
	Fontion Main principale
	'''
	root = Tk()
	root.resizable(width=FALSE, height=FALSE)
	root.wm_title("Builder")
	app = GUI(root)
	root.mainloop()


main()
