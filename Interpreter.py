#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
AKKAL Aghilas
BELKACEM Liza
'''

import Leap, os, thread, time, random, math, pickle, threading, utils, tkMessageBox
from time import sleep
from random import shuffle
from Queue import deque
from NBClassifier import NB
from Tkinter import *


class GUI:
	'''
	Classe de la fenetre principale
	'''

	def __init__(self, master):
		'''
		Initier la fenetre
		'''
		self.master = master
		self.master.protocol('WM_DELETE_WINDOW', self.close)

		self.output = StringVar()
		Label(self.master, textvariable=self.output, font=('Helvetica', 16)).pack(expand=True)

		self.controller = Leap.Controller()
		sleep(0.01)

		# charger la dataset
		dataset = []
		if os.path.exists('dataset.p'):
			with open('dataset.p', 'rb') as f:
				try:
					dataset = pickle.load(f)
					if not len(dataset):
						self.master.update()
						tkMessageBox.showwarning('', 'Pas de signe dans la dataset.' + \
							"\nVeuiller créer des signes à l'aide de 'Builder.py'")
						exit()

					# Valider le contenue de dataset
					for sign in dataset:
						if not isinstance(sign, utils.Sign):
							self.master.update()
							tkMessageBox.showwarning('', \
								"Invalid 'dataset.p'.\n" + \
								"Use 'Builder.py' to generate a 'dataset.p'.")
							exit()
				except Exception:
					self.master.update()
					tkMessageBox.showwarning('', "Error reading 'dataset.p'")
					exit()
		else:
			self.master.update()
			tkMessageBox.showwarning('', "Missing 'dataset.p'")
			exit()

		# Ordonner les signes par types
		fixed, gestures = [], []
		for sign in dataset:
			if len(sign.samples) >= 2:
				if not utils.validateFeatures(sign.samples):
					self.master.update()
					tkMessageBox.showwarning('', \
					"Valeurs non nulles trouvées dans le signe '" + sign.value \
					+ "', Veuillez supprimer les captures et re-enregistrer à l'aide de 'Builder.py'")
					exit()

				if sign.type == 'Fixed':
					for sample in sign.samples:
						# Filtrer les captures de longeurs incorrecte
						if len(sample) == 17:
							fixed.append((sign.value, sample))
				else:
					for sample in sign.samples:
						# Filtrer les captures de longeurs incorrecte
						if len(sample) == 200:
							gestures.append((sign.value, sample))
			else:
				self.master.update()
				tkMessageBox.showwarning('', \
					"signe '" + sign.value + \
					"' Ignoré.\nAu minimum 2 captures sont requises.")

		# Creation et training du classificateur pour les signes fixes
		self.nbFixed = None
		self.nbGesture = None

		if len(fixed):
			self.nbFixed = NB()
			self.nbFixed.train(fixed)

		if len(gestures):
			self.nbGesture = NB()
			self.nbGesture.train(gestures)

		# Lancement du thread pour la capture
		self.keepAlive = True
		thread = threading.Thread(target=self.interpret)
		thread.start()


	def classify(self, _buffer, fixed):
		'''
		Classifie le signe selont l'input et affiche un message
		'''
		result = None

		# Classifie les signes fixes
		if fixed and self.nbFixed:
			result = self.nbFixed.probabilities(utils.vectorize(_buffer, fixed=True))

		# Classifie les signes gestuelles
		elif self.nbGesture:
			result = self.nbGesture.probabilities(utils.vectorize(_buffer, fixed=False))

		# Detection basée sur les résultats de la distance euclidienne
		if result[0][2] < 0.85:
			self.output.set(result[0][0])
		else:
			self.output.set("non reconnue ...")
		sleep(3)
		self.output.set("")


	def close(self):
		'''
		Ferme le programme, attendre que le thread de l'interpreteur qu'il finisse pour arreter tout
		'''
		self.keepAlive = False
		sleep(0.5)
		self.master.destroy()
		exit()


	def interpret(self):
		'''
		Thread de l'interpreteur principale, detecte les signes fixes ou mouvement
		'''
		moving = False

		# Capture toute les frames
		mainBuffer = []

		# Enregistre les frames qui ont un mouvement
		motionBuffer = []

		# Enregistre les frames fixes
		fixedBuffer = []

		# un delais de 0.3 secondes pour rendre la detection plus fluide
		stateBuffer = deque(maxlen=30)

		# Boolean du controleur (leap) assumé connecté
		wasConnected = True

		while self.keepAlive:

			# Affiche un message indicant que la leap à été connecté
			if self.controller.is_connected:
				if not wasConnected:
					wasConnected = True
					self.master.update()
					tkMessageBox.showwarning('', 'Leap Motion connectée!')

				# Capture a peu pres 100 frames par secondes
				sleep(0.01)

				# Si au moin une main est en vue, lance la capture
				if len(self.controller.frame().hands) > 0:

					# append la premiere main en vue
					hand = self.controller.frame().hands[0]
					mainBuffer.append(hand)

					# Vérifie si c'est une gestuelle ou bien fixe
					if len(mainBuffer) > 10:

						if utils.moving(mainBuffer[-10], mainBuffer[-1]):
							stateBuffer.append(1)
						else:
							stateBuffer.append(0)

						# Still moving -> keep filling moving buffer
						if sum(stateBuffer) > 15:
							if not moving:
								moving = True
								fixedBuffer = []
							motionBuffer.append(hand)

						else:
							# Si plus de mouvements, analyser
							if len(motionBuffer) > 30:
								self.classify(motionBuffer, False)
								moving = False
								mainBuffer = []
								motionBuffer = []
								fixedBuffer = []

							# Signe fixé pour 0.4 sec, analyzer
							elif len(fixedBuffer) > 40:
								self.classify(fixedBuffer, True)
								mainBuffer = []
								motionBuffer = []
								fixedBuffer = []

							# Si main est fixe, remplir le buffer fixe
							else:
								fixedBuffer.append(hand)

				# Si main hors champs de vision, analyser si on a capturer plus de 30 frames
				else:
					if len(motionBuffer) > 30:
						self.classify(motionBuffer, False)
						sleep(0.01)
					mainBuffer = []
					motionBuffer = []

			else:
				# Affiche un message indicant que la leap à été déconnecté
				if wasConnected:
					wasConnected = False
					self.master.update()
					tkMessageBox.showwarning('', 'Leap Motion déconnectée!')


def main():
	'''
	Fontion Main principale
	'''
	root = Tk()
	root.resizable(width=FALSE, height=FALSE)
	root.geometry('{}x{}'.format(300, 150))
	root.wm_title("Interpreter")

	app = GUI(root)
	root.mainloop()


main()
