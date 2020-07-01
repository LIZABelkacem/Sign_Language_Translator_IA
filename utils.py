#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
AKKAL Aghilas
BELKACEM Liza
'''


import Leap, math

class Sign:
	'''
	Classe principales des signes
	'''
	def __init__(self, value, _type='Undefined', samples=[]):
		self.value = value
		self.type = _type # Type soit (fixe) ou (gestuelle)
		self.samples = samples


def moving(handThen, handNow):
	'''
	Determiner si ya eu mouvement entre deux frames successives
	'''
	total = []
	for x, y in zip(extractFeatures(handThen), extractFeatures(handNow)):
		total.append(abs(x - y))
	z = sum(total) / float(len(total))

	# Seuile qui parait suffisant pour dire que ya eu mouvement
	return z > 4.7


def vectorize(_buffer, fixed):
	'''
	Vecteuriser les signes capturés
	'''
	# Pour les signes fixé
	if fixed:
		return compress([extractFeatures(x) for x in _buffer], 1)[:17]

	# Pour les signes gestuelles
	return compress(normalize([extractFeatures(x) for x in _buffer]), 10)


def extractFeatures(hand):
	'''
	Extrait les caractéristiques depuis la main
	retourne un vecteur de la position XYZ des doigts,
	de la rotation de la main, ainsi que la position de la main
	'''
	featureVector = []
	# Les XYZ pour chaque doigts
	for finger in hand.fingers:
		normalized = finger.bone(3).center - hand.palm_position
		featureVector.extend((normalized.x, normalized.y, normalized.z))

	# La rotation de la main (pitch et roll)
	featureVector.append(math.degrees(hand.direction.pitch))
	featureVector.append(math.degrees(hand.direction.roll))

	# Le XYZ de la main
	palmPosition = hand.palm_position
	featureVector.extend((palmPosition.x, palmPosition.y, palmPosition.z))
	return featureVector


def normalize(_buffer):
	'''
	Normalise une sequence de frames
	'''
	startPoints = []
	output = []
	for i in range(15,20):
		startPoints.append(_buffer[0][i])
	for vector in _buffer:
		for i, j in zip(range(15, 20), range(5)):
			vector[i] = vector[i] - startPoints[j]
		output.append(vector)
	return output


def compress(_buffer, size):
	'''
	Compresse une sequence de frames vers un nombre fixe de keyframes
	pour simplifier la comparaison entre les séquences
	'''
	# Determine combient de frames a compresser en une seule keyframe
	step = len(_buffer)/size

	output = []
	for i in range(size):
		average = [0 for j in range(len(_buffer[0]))]
		for vector in _buffer[i * step:(i + 1) * step]:
			average = [q + w for q, w in zip(vector, average)]
		output.extend(map(lambda x : x / float(step), average))
	return output


def validateFeatures(samples):
	'''
	Vérifie qu'il n'ya pas de valeurs nulles dans les captures des caractéristiques
	pour ne pas causer d'erruer mathematique lors d'un log(0)
	'''
	for feature in zip(*samples):
		if not sum(feature):
			return False
	return True
