
# The Object Oriented implementation of Sexually Antagonistic mutation accumulation
#     in Inversions in a forward Population simulation
# Ideally, models large inversion polymorphisms in populations with high reproductive skew



# class InputError(Exception):
#     """Exception raised for errors in the input.

#     Attributes:
#         expression -- input expression in which the error occurred
#         message -- explanation of the error
#     """

#     def __init__(self, expression, message):
#         self.expression = expression
#         self.message = message


# REWRITE WITH NUMPY ARRAYS/VECTORS?

import numpy as np

# The object representing an individual in the population under simulation,
# contains methods for generating mutation position and effects, and new recombinant gametes
# recombRate is the expected number of recombination events per chromosome per reproductive event
# meanMutEffect is the expected effect size of a new mutation
# mutEffectDiffSD is the SD of the difference in survival/rep effect size of a new mutation (normal dist)
# genome defaults to 2 copies of a single chormosome,
# ideally: genome = [[[chr1hom1],[chr1hom2]],[[chr2hom1],[chr2hom2]],..]
class individual(object):
	"""individuals represent members of simSAIpopulations"""
	def __init__(self, sex, mutEffectDiffSD, recombRate, conversionRate, minInvLen,
			isFly, genome = [[[[],[]],[[],[]]]]):
		# super(individual, self).__init__()
		self.sex = sex
		self.mutEffectDiffSD = mutEffectDiffSD
		self.recombRate = recombRate
		self.conversionRate = conversionRate
		self.minInvLen = minInvLen
		# CONSIDER JUST PASSING VARIABLES WHEN NEEDED
		self.isFly = isFly
		# genome = [[[chr1hom1],[chr1hom2]],[[chr2hom1],[chr2hom2]],..]
		# where chomosome homologs = [mutist, InvList]
		self.genome = genome


	# For getting the insertion index of a position from a list of [position,..] lists
	def __getInsInd(self,mutInvList,mutInvPos):
		i = 0
		while (i < len(mutInvList)) and (mutInvList[i][0] <= mutInvPos):
			i += 1
		return i

	# For inserting a mutation/inversion into a corresponding list
	# May rely on passing the list as a reference (doesn't currently)
	def __insert(self,mutInvList,mutInv):
		i = 0
		while (i < len(mutInvList)) and (mutInvList[i][0] <= mutInv[0]):
			i += 1
		mutInvList[i:i] = [mutInv]
		return mutInvList


	# generates mutations
	# MAKE THIS BIOLOGICALLY RELEVANT? SETTLE ON A DISTRIBUTION - lognormal?
	def __genEffectSizes(self):
		base = np.random.ranf()
		offset = np.random.normal(scale=self.mutEffectDiffSD)
		mutEffects = []
		while (min(1-base,base) < offset) or (offset < max(base-1,-base)):
			offset = np.random.normal(scale=self.mutEffectDiffSD)

		# # For modeling effects multiplicatively?
		# return [base+offset,base+offset]

		# Survival mult., Quality additive
		return [1-base+offset,base+offset]

	#Generates a mutation of the form [position, survival effect, rep effect, ID]
	def mutate(self,ID):
		# print self.genome
		mutPos = np.random.ranf()
		mutEffects = self.__genEffectSizes()
		mutation = [mutPos]+mutEffects+[ID]
		# Pick a chromosome
		chromIndex = np.random.randint(0,len(self.genome))
		# Put it on one of the two homologs
		homIndex = np.random.randint(0,2)
		# print self.genome[chromIndex][homIndex][0]
		self.genome[chromIndex][homIndex][0] = self.__insert(self.genome[chromIndex][homIndex][0],mutation)
		# print self.genome[chromIndex][homIndex][0]
		# Return the mutation data for recording
		return mutation[0:3]+[chromIndex]

	# Generates and inserts an inversion into the genome, unless there is no open region >= minInvLen
	# Inversions cover the region [pos1,pos2)
	# Does not use resampling 
	def mutateInv(self,ID):
		# Pick a chromosome
		chromIndex = np.random.randint(0,len(self.genome))
		# Put it on one of the two homologs
		homIndex = np.random.randint(0,2)
		chromHomInv = self.genome[chromIndex][homIndex][1]
		# Pick where the insertion may be placed
		openRegLengths = []
		openRegStarts = []
		openRegIndexes = []
		potentialStart = 0
		index = 0
		for inversion in chromHomInv:
			length = inversion[0] - potentialStart
			if length > self.minInvLen:
				openRegLengths += [length]
				openRegStarts += [potentialStart]
				openRegIndexes += [index]
			potentialStart = inversion[1]
			index += 1
		length = 1 - potentialStart
		if length > self.minInvLen:
			openRegLengths += [length]
			openRegStarts += [potentialStart]
			openRegIndexes += [index]
		# If there is no space for a new inversion >= minInvLen, don't add one, return None
		if len(openRegStarts) == 0:
			return
		# Now sample which open region to add the inversion to
		regChoice = np.random.choice(len(openRegStarts),p=[l/sum(openRegLengths) for l in openRegLengths])
		# Generate the inversion
		posA = openRegStarts[regChoice] + np.random.ranf()*openRegLengths[regChoice]
		posB = openRegStarts[regChoice] + np.random.ranf()*openRegLengths[regChoice]
		inversion = [min(posA,posB),max(posA,posB),ID]
		index = openRegIndexes[regChoice]
		chromHomInv[index:index] = [inversion]
		# Return the inversion data to record
		return inversion[0:2]+[chromIndex]

	# For updating the repQuality and survival if pre-calculated
	# Not currently used (obviously)
	def updatePhenotypes(self):
		return

	# Negative survival effects are independent and multiplicative
	def survival(self):
		survival = 1.0
		for chrom in self.genome:
			for mut in chrom[0][0]:
				survival *= mut[1]
			for mut in chrom[1][0]:
				survival *= mut[1]
		return survival

	# FIX THIS - what quality accounting process is biological? (This doesn't seem tooo bad, tbh)
	# ALSO - maybe calculate it once to save time? probably recalculated several times in choosing fathers
	def repQuality(self):
		quality = 1.0
		for chrom in self.genome:
			for mut in chrom[0][0]:
				quality += mut[2]
				# For modeling effects multiplicatively? - requires changing effect generation
				# quality *= mut[2]
			for mut in chrom[1][0]:
				quality += mut[2]
				# For modeling effects multiplicatively? - requires changing effect generation
				# quality *= mut[2]
		return quality

	# Takes a chromosome and returns the chromosome with converted mutations
	# May want to allow for a boolean hasConversion to turn this off in the simulation
	def __convertChrom(self,chrom):
		homInd1 = 0
		homInd2 = 0
		# Check for heterozygosity and add/remove mutations following conversionRate probability
		# Relies on the invariant that earlier indexed mutations have earlier position
		while homInd1 < len(chrom[0][0]) and homInd2 < len(chrom[1][0]):
			mut1 = chrom[0][0][homInd1]
			mut2 = chrom[1][0][homInd2]
			if mut1[0] == mut2[0]:
				homInd1 += 1
				homInd2 += 1
			if mut1[0] < mut2[0]:
				if np.random.ranf < self.conversionRate:
					if np.random.randint(2):
						chrom[0][0][homInd1:homInd1+1] = []
					else:
						chrom[1][0][homInd2-1:homInd2-1] = [mut1]
						homInd2 += 1
						homInd1 += 1
				else:
					homInd1 += 1
			if mut1[0] > mut2[0]:
				if np.random.ranf < self.conversionRate:
					if np.random.randint(2):
						chrom[1][0][homInd2:homInd2+1] = []
					else:
						chrom[0][0][homInd1-1:homInd1-1] = [mut2]
						homInd1 += 1
						homInd2 += 1
				else:
					homInd2 += 1
		# Deal with the remaining mutations
		# when one chromosome has no mutations it is dealt with here immediately
		while homInd1 < len(chrom[0][0]):
			if np.random.ranf < self.conversionRate:
				if np.random.randint(2):
					chrom[0][0][homInd1:homInd1+1] = []
				else:
					chrom[1][0] += [chrom[0][0][homInd1]]
					homInd1 += 1
			else:
				homInd1 += 1
		while homInd2 < len(chrom[1][0]):
			if np.random.ranf < self.conversionRate:
				if np.random.randint(2):
					chrom[1][0][homInd2:homInd2+1] = []
				else:
					chrom[0][0] += [chrom[1][0][homInd2]]
					homInd2 += 1
			else:
				homInd2 += 1
		return chrom


	# Takes two inversion lists for homologous chromosomes,
	# indexes of the closest inversions to start <= the position of interest,
	# and the position of interest
	# Returns the position following the position of interest such that an odd # of crossovers
	# between the two would generate aneuploid gametes, returns -1 if it isn't in such a region
	def __getAneupRegion(self,invHom1,invHom2,ind1,ind2,recPos):
		# Deal with no inversions present on the chromosome
		if len(invHom1) == 0:
			if (len(invHom2) == 0) or (recPos >= invHom2[ind2][1]):
				return -1
			else:
				return invHom2[ind2][1]
		elif len(invHom2) == 0:
			if recPos >= invHom1[ind1][1]:
				return -1
			else:
				return invHom1[ind1][1]
		else:
			end1 = invHom1[ind1][1]
			end2 = invHom2[ind2][1]
			# Currently, inversions are counted as [1,2), so crossovers are inside or not following such
			if recPos < end1:
				if recPos < end2:
					return min(end1,end2)
				if (ind2 < len(invHom2)-1) and invHom2[ind2+1][0] < end1:
					return invHom2[ind2+1][0]
				return end1
			elif recPos < end2:
				if (ind1 < len(invHom1)-1) and invHom1[ind1+1][0] < end2:
					return invHom1[ind1+1][0]
				return end2
			else:
				return -1

	# Model independently per chromosome, currently doesn't redraw if recombination events fail,
	# just throws out all recombination events in an aneuploidy-causing region if they are odd in number
	def genGamete(self):
		gamGenome = []
		for parChrom in self.genome:
			numRecomb = np.random.poisson(self.recombRate)
			currHom1 = bool(np.random.randint(2))
			# This first copy step is necessary independent of conversion activity, 
			# to prevent changes to shared-referent chromosomes
			chrom = [[list(parChrom[0][0]),list(parChrom[0][1])],[list(parChrom[1][0]),list(parChrom[1][1])]]
			# Perform fly-specific non-recombination non-conversion check for males
			if self.sex == 'F' or (not self.isFly):
				chrom = self.__convertChrom(chrom)
			if numRecomb == 0 or (self.isFly and self.sex == 'M'):
				if currHom1:
					gamGenome += [chrom[0]]
				else:
					gamGenome += [chrom[1]]
			else:
				recombPositions = np.random.ranf(numRecomb)
				
				# Construct a recombinant gamete from the recombination positions
				gamMutations = []
				gamInversions = []

				
				recIndex = 0

				invInd1 = 0
				invInd2 = 0
				invHom1 = chrom[0][1]
				invHom2 = chrom[1][1]
				mutInd1 = 0
				mutInd2 = 0

				prevInvInd1 = 0
				prevInvInd2 = 0
				prevMutInd1 = 0
				prevMutInd2 = 0

				while recIndex < numRecomb:
					recPos = recombPositions[recIndex]
					while (mutInd1 < len(chrom[0][0])) and (chrom[0][0][mutInd1][0] <= recPos):
						mutInd1 += 1
					while (mutInd2 < len(chrom[1][0])) and (chrom[1][0][mutInd2][0] <= recPos):
						mutInd2 += 1
					while (invInd1 < len(chrom[0][1])) and (chrom[0][1][invInd1][0] <= recPos):
						invInd1 += 1
					while (invInd2 < len(chrom[1][1])) and (chrom[1][1][invInd2][0] <= recPos):
						invInd2 += 1
					# Add the mutations and inversions to the gamete chromosome
					if currHom1:
						gamMutations += chrom[0][0][prevMutInd1:mutInd1]
						gamInversions += chrom[0][1][prevInvInd1:invInd1]
					else:
						gamMutations += chrom[1][0][prevMutInd2:mutInd2]
						gamInversions += chrom[1][1][prevInvInd2:invInd2]
					# Update the mutation/inversion indexes of the previous breakpoint
					prevInvInd1 = invInd1
					prevInvInd2 = invInd2
					prevMutInd1 = mutInd1
					prevMutInd2 = mutInd2
					# Deal with crossovers in regions potentially generating aneuploidy
					aneupRegEnd = self.__getAneupRegion(invHom1,invHom2,invInd1-1,invInd2-1,recPos)
					if aneupRegEnd == -1:
						currHom1 = not currHom1
						recIndex += 1
					else:
						otherRecInReg = []
						recIndex += 1
						while (recIndex < numRecomb) and (recombPositions[recIndex] < aneupRegEnd):
							otherRecInReg += [recombPositions[recIndex]]
							recIndex += 1
						# If there's an even number of recombinations in the region in total:
						if len(otherRecInReg)%2:
							currHom1 = not currHom1
							for recPos in otherRecInReg:
								while (mutInd1 < len(chrom[0][0])) and (chrom[0][0][mutInd1][0] <= recPos):
									mutInd1 += 1
								while (mutInd2 < len(chrom[1][0])) and (chrom[1][0][mutInd2][0] <= recPos):
									mutInd2 += 1
								# Add the mutations to the gamete chromosome (no inversion change in region)
								if currHom1:
									gamMutations += chrom[0][0][prevMutInd1:mutInd1]
								else:
									gamMutations += chrom[1][0][prevMutInd2:mutInd2]
								# Update the mutation indexes of the previous breakpoint
								prevMutInd1 = mutInd1
								prevMutInd2 = mutInd2
								# Switch the current chromosome from the crossover event
								currHom1 = not currHom1
				# Add the last mutations and inversions to the gamete chromosome
				if currHom1:
					gamMutations += chrom[0][0][prevMutInd1:len(chrom[0][0])]
					gamInversions += chrom[0][1][prevInvInd1:len(chrom[0][1])]
				else:
					gamMutations += chrom[1][0][prevMutInd2:len(chrom[1][0])]
					gamInversions += chrom[1][1][prevInvInd2:len(chrom[1][1])]
				gamGenome += [[gamMutations,gamInversions]]
		return gamGenome




		
# The object representing the population under simulation, contains methods for stepping through generations
# size is the population size
# mutRate is the expected number of new mutations per chromosome per reproductive event
# mutRateInv is the expected number of new inversions per chromosome per reproductive event
# mutEffectDiffSD is the SD of normally distributed offset of survival/rep mutation effects
#    offsetting from [x,1-x], with x = uniform[0,1)
# minInvLen is the minimum length of a new inversion
# conversionRate is the probability heterozygous locus that a conversion occurs, direction is random
# recombRate is the expected number of recombination events per chromosome per reproductive event
# encounterNum is the number of males a female chooses from in a reproductive event
# choiceNoiseSD is the SD for the normally distributed additive noise to male quality in the female choice
# record is a general variable for storing generation statistics about the population, see __updateRecord
# invRecBuffer is the distance outside of inversion boundaries in which to record mutations for an inversion
# CONSIDER USING A 'PARAMETERS' PASSED LIST
class simSAIpopulation(object):
	"""simSAIpopulation represents populations for sexually antagonistic inversion simulation"""
	def __init__(self, size, mutRate, mutRateInv, mutEffectDiffSD, minInvLen, conversionRate,
			recombRate, encounterNum, choiceNoiseSD, invRecBuffer, isFly = True, randomSex = True,
			genomes = [], sexes = [], record = [[],[],[],[],[],[],[],[]]):
		# super(simSAIpopulation, self).__init__()
		self.size = size
		self.mutRate = mutRate
		self.mutRateInv = mutRateInv
		self.expectedNumMut = mutRate * size
		self.expectedNumInvMut = mutRateInv * size
		# Keep trck of next mutation (or inversion?) ID
		self.__mutIDcount = 0
		self.__invIDcount = 0
		self.mutEffectDiffSD = mutEffectDiffSD
		self.minInvLen = minInvLen
		self.conversionRate = conversionRate
		self.recombRate = recombRate
		self.encounterNum = encounterNum
		self.choiceNoiseSD = choiceNoiseSD
		self.males = []
		self.females = []
		# For modeling D.mel specific recombination/other biology
		self.isFly = isFly
		# Record keeping variables, record data structure defined in __updateRecord
		self.invRecBuffer = invRecBuffer
		self.record = record
		self.age = 0
		# Handling input and default populations
		numGenomes = len(genomes)
		if numGenomes > size:
			raise InputError(genomes,'More genomes provided than population size')
		elif len(sexes) != 0 or len(sexes) != numGenomes:
			raise InputError(sexes,'Sexes must be of equal length to genomes')
		else:
			for i in range(numGenomes):
				if sexes[i] == 'F':
					self.females += [individual('F',mutEffectDiffSD,recombRate,conversionRate,minInvLen,genomes[i])]
				else:
					self.males += [individual('M',mutEffectDiffSD,recombRate,conversionRate,minInvLen,genomes[i])]
			numLeft = size-numGenomes
			if len(self.females) < 1:
				numLeft -= 1
				self.females += [individual('F',mutEffectDiffSD,recombRate,conversionRate,minInvLen)]
			if len(self.males) < 1:
				numLeft -= 1
				self.males += [individual('M',mutEffectDiffSD,recombRate,conversionRate,minInvLen)]
			# Generate the remaining set of 'size' individuals
			#   with random or equal probability sex and no mutations or inversions
			if randomSex:
				numMales = np.random.binomial(numLeft,0.5)
			else:
				numMales = int(numLeft/2)
			self.males += [individual('M',mutEffectDiffSD,recombRate,conversionRate,minInvLen,isFly) for i in range(numMales)]
			self.females += [individual('F',mutEffectDiffSD,recombRate,conversionRate,minInvLen,isFly) for j in range(numLeft-numMales)]
			self.__updateRecord()

	class InputError(Exception):
		"""Exception raised for errors in the input.

		Attributes:
			expression -- input expression in which the error occurred
			message -- explanation of the error
		"""

		def __init__(self, expression, message):
			self.expression = expression
			self.message = message

	# For generating a set of genomes, sexes, and a record from specified mutations and inversions, 
	# input lists formatted as described in self.record but with count instead of initial generation:
	# mutList: a list of all mutations, indexed by ID, with each entry as 
	#      [position,survival effect,reproductive effect,chromosome,initial count]
	# populates the remaining genome slots with genomes to which mutations are randomly assigned from the count pools
	# Currently doesn't allow description of prior record
	# How to model starting with mutations specific to sexes?
	# Limit the number of further genomes to generate? How will this interact with having at least 1 'M'/'F'?
	@staticmethod
	def genGenomesSexes(size, mutList, invList, randomSex = True,
			genomes = [], sexes = []):
		# Handling input
		numGenomes = len(genomes)
		if numGenomes > size:
			raise InputError(genomes,'More genomes provided than population size')
		# Either require equal length sexes and genomes or just that sexes is smaller than population size
		#   and allows for one of each sex?
		elif len(sexes) != 0 or len(sexes) != numGenomes:
			raise InputError(sexes,'Sexes must be of equal length to genomes')
		# Generate the remaining sexes list
		numFemales = 0
		numMales = 0
		for sex in sexes:
			if sex == 'M':
				numMales += 1
			elif sex == 'F':
				numFemales += 1
			else:
				raise InputError(sexes,'Sexes must only contain \'F\' and \'M\' elements')
		if numMales == 0:
			sexes += ['M']
			numMales += 1
		if numFemales == 0:
			sexes += ['F']
			numFemales += 1
		numRemaining = size - numFemales - numMales
		if numRemaining < 0:
			raise InputError(sexes,'Sexes must allow at least one \'F\' and \'M\' in the population')
		# Reuse numMales for the number of males to be added
		if randomSex:
			numMales = np.random.binomial(numRemaining,0.5)
		else:
			numMales = int(numRemaining/2)
		sexes += ['M' for i in range(numMales)]
		sexes += ['F' for i in range(numRemaining-numMales)]
		# Generate the remaining genomes
		newGenomes = []
		numNewGenomes = size-numGenomes
		posOrderedMut = []
		posOrderedInv = []
		# Record should be returned with only [1,3] actually populated, [2,4..7] with empty lists 
		#   for 0th generation update
		record = [[],[],[],[],[],[],[],[]]
		for m in range(len(mutList)):
			count = mutList[m][4]
			if count >
			mutation = mutList[m][0:3]+[m]
			record[1] += [mutList[m][0:4]+[0]]
			record[2] += [[]]
		for i in range(len(invList)):
			mutation = mutList[m][0:3]+[m]
			record[1] += [mutList[m][0:4]+[0]]
			record[2] += [[]]

		return (genomes,sexes,record)

	# For changing the population size during simulation
	def setSize(self,newSize):
		self.size = newSize
		return

	# Removes inversions that are fixed in the population,
	# changes the position of internal mutations to reflect true position (flips around the center of the inversion)
	# the old position of the mutations is lost
	# WORTH IMPROVING PERFORMANCE: merge with record keeping in record generations? also reduce loop number
	def __removeFixedInv(self):
		wholePop = self.males + self.females
		invCounts = [0]*self.__invIDcount
		invPos = []*self.__invIDcount
		# All mutations are passed as references, so don't want to change more than one
		firstMutEncounter = [True]*self.__mutIDcount

		inversionRemoved = False
		# Generate count and position data
		for i in range(len(wholePop)):
			for c in range(len(indiv.genome)):
				for h in range(2):
					chromHomInv = wholePop[i].genome[c][h][1]
					for invIndex in range(len(chromHomInv)):
						inversion = chromHomInv[invIndex]
						invCounts[inversion[2]] += 1
						invPos[inversion[2]] += [[i,c,h,invIndex]]
		for ID in range(self.__invIDcount):
			if invCounts[ID] == 2*self.size:
				inversionRemoved = True
				inversion = self.record[3][ID]
				length = self.record[3][ID][1] - self.record[3][ID][0]
				invCenter = self.record[3][ID][0] + length/2.0
				for [i,c,h,invIndex] in invPos[ID]:
					# Remove the inversion
					wholePop[i].genome[c][h][1][invIndex:invIndex+1] = []
					# Rearrange the mutation positions to reflect the loss of inversion data
					mutHom = wholePop[i].genome[c][h][0]
					index = 0
					mutInside = []
					while index < len(mutHom) and mutHom[index][0] < inversion[0]:
						index += 1
					startIndex = index
					while index < len(mutHom) and mutHom[index][0] < inversion[1]:
						mutInside = [mutHom[index]] + mutInside
						index += 1
					# Replace the mutations inside with ones in inverted order
					mutHom[startIndex:index] = mutInside
					# Flip the mutation positions around the center of the removed inversion
					for mut in mutInside:
						if firstMutEncounter[mut[3]]:
							firstMutEncounter[mut[3]] = False
							# Flip the mutation across the center
							mut[0] = 2*invCenter-mut[0]
						print mut
			# elif invCounts[i] > 2*self.size:
			# 	print "Error: more inversions than alleles possible for ID " + str(i)
		return inversionRemoved

	# Simulating a single generational step
	def step(self):
		# print "Generation " + str(self.age) + " Reproduction"
		# Pick mothers
		femaleSurvivals = []
		for female in self.females:
			# print female.genome
			femaleSurvivals += [female.survival()]
		# print "Female Survivals:" + str(femaleSurvivals)
		femaleSurvivals = [s/sum(femaleSurvivals) for s in femaleSurvivals]
		motherIndexes = np.random.choice(len(femaleSurvivals),self.size,p=femaleSurvivals)

		# Calculate necessary male values
		maleSurvivals = []
		# maleGenQuality = []
		for male in self.males:
			# print male.genome
			maleSurvivals += [male.survival()]
			# maleGenQuality += [male.repQuality()]
		# print "Male Survivals:" + str(maleSurvivals)
		maleSurvivals = [s/sum(maleSurvivals) for s in maleSurvivals]

		# Populate the next generation by choosing fathers per mother and generating child genomes
		newMales = []
		newFemales = []
		# numMales = 0
		# numExpectedMales = int(self.size/2)
		for motherIndex in motherIndexes:
			mother = self.females[motherIndex]

			encounteredMaleIndexes = np.random.choice(len(maleSurvivals),self.encounterNum,p=maleSurvivals)
			fatherIndex = encounteredMaleIndexes[0]
			# maxScore = self.males[fatherIndex].repQuality() + np.random.normal(scale=self.choiceNoiseSD)
			maxScore = 0 # (assumes rep quality score >= 0)
			for f in encounteredMaleIndexes:
				score = self.males[f].repQuality() + np.random.normal(scale=self.choiceNoiseSD)
				if score > maxScore:
					fatherIndex = f
					maxScore = score
			father = self.males[fatherIndex]

			# Generate the genome of the new member from the parents
			genome = []
			fatherGamete = father.genGamete()
			# print "father gamete" + str(fatherGamete)
			motherGamete = mother.genGamete()
			# print "mother gamete" + str(motherGamete)
			for chrom in range(len(fatherGamete)):
				genome += [[fatherGamete[chrom],motherGamete[chrom]]]
			# print genome

			# Instantiate the new population member with a random sex
			if np.random.randint(2):
				newFemales += [individual('F',self.mutEffectDiffSD,self.recombRate,self.conversionRate,self.minInvLen,self.isFly,genome)]
			else:
				newMales += [individual('M',self.mutEffectDiffSD,self.recombRate,self.conversionRate,self.minInvLen,self.isFly,genome)]

		self.females = newFemales
		self.males = newMales

		# Remove fixed inversions and rearrange internal mutations
		self.__removeFixedInv()

		# Update the age of the population
		self.age = self.age + 1

		# print "Generation " + str(self.age) + " Mutation"
		# Sprinkle on mutations
		wholePop = self.males + self.females
		# Add new SA mutations
		numMuts = np.random.poisson(self.expectedNumMut)
		indivWithMut = np.random.randint(self.size, size=numMuts)
		for i in indivWithMut:
			self.record[1] += [wholePop[i].mutate(self.__mutIDcount) + [self.age]]
			self.__mutIDcount += 1
			# self.record[2] += [[0]*self.age]
			self.record[2] += [[0 for t in range(len(self.record[0]))]]
		# Add new inversions
		numInvMuts = np.random.poisson(self.expectedNumInvMut)
		indivWithInvMut = np.random.randint(self.size, size=numMuts)
		for i in indivWithInvMut:
			# Must account for failure due to no space on the genome
			invData = wholePop[i].mutateInv(self.__invIDcount)
			if not invData is None:
				self.record[3] += [invData + [self.age]]
				self.__invIDcount += 1
				# self.record[4] += [[0]*self.age]
				# self.record[4] += [(self.age,0)]
				self.record[4] += [[0 for t in range(len(self.record[0]))]]
				self.record[5] += [[0 for t in range(len(self.record[0]))]]
				self.record[6] += [[0 for t in range(len(self.record[0]))]]
				self.record[7] += [[0 for t in range(len(self.record[0]))]]
		# Could update phenotype values here
		return

	# For updating all recorded information on the population, record structured as:
	# [0] a list of ages at which an update was made
	# [1] a list of all mutations, indexed by ID, with each entry as 
	#      [position,survival effect,reproductive effect,chromosome,age at which mutation occured]
	# [2] a list of counts, indexed by ID, of the mutation at each age noted in [0]
	# [3] a list of all inversions, indexed by ID, with each entry as 
	#      [start position,end position,chromosome,age at which mutation occured]
	# [4] a list of counts, indexed by ID, of the inversion at each age noted in [0]
	# [5] a list of average count of mutations within the buffer region across the entire population,
	#      indexed by ID, of each inversion at each age noted in [0]
	# [6] a list of average survival effect within buffer region across the entire population,
	#      indexed by ID, of each inversion at each age noted in [0]
	# [7] a list of average reproductive effect within buffer region across the entire population,
	#      indexed by ID, of each inversion at each age noted in [0]
	# ADD: pop size for changing pop size?
	def __updateRecord(self):
	 	# print "Record Update"
		# Record the age of the record update
		self.record[0] += [self.age]
		# Count the number of each mutation/ID
		mutCounts = [0]*self.__mutIDcount
		invCounts = [0]*self.__invIDcount
		numMutInBuffer = [0]*self.__invIDcount
		# survEffectTotalInBuffer = [0]*self.__invIDcount
		survEffectTotalInBufferMultiplicative = [0]*self.__invIDcount
		reprEffectTotalInBuffer = [0]*self.__invIDcount
		for indiv in self.males + self.females:
			for chrom in indiv.genome:
				for hom in chrom:
					for mut in hom[0]:
						mutCounts[mut[3]] += 1
					lowerMutInd = 0
					upperMutInd = 0
					for inv in hom[1]:
						invCounts[inv[2]] += 1
						while lowerMutInd < len(hom[0]) and hom[0][lowerMutInd][0] < inv[0]-self.invRecBuffer:
							lowerMutInd += 1
						while upperMutInd < len(hom[0]) and hom[0][upperMutInd][0] < inv[1]+self.invRecBuffer:
							upperMutInd += 1
						mutInside = hom[0][lowerMutInd:upperMutInd]
						# Account for multiplicative survival effects - average effect is average of multiplied effects
						numMutInside = 0
						thisSurvEffect = 1
						thisReprEffect = 0
						for mut in mutInside:
							numMutInside += 1
							thisSurvEffect *= mut[1]
							thisReprEffect += mut[2]
						numMutInBuffer[inv[2]] += numMutInside
						survEffectTotalInBufferMultiplicative[inv[2]] += thisSurvEffect
						reprEffectTotalInBuffer[inv[2]] += thisReprEffect
		# Update the record, get averages for record[5,6,7]
		for i in range(self.__mutIDcount):
			self.record[2][i] += [mutCounts[i]]
		for j in range(self.__invIDcount):
			count = invCounts[j]
			# If no members of the inversion ID left, record averages as -1 ?
			if count == 0:
				self.record[4][j] += [count]
				self.record[5][j] += [-1]
				self.record[6][j] += [-1]
				self.record[7][j] += [-1]
			else:
				self.record[4][j] += [count]
				self.record[5][j] += [numMutInBuffer[j]/(float(count))]
				self.record[6][j] += [survEffectTotalInBufferMultiplicative[j]/(float(count))]
				self.record[7][j] += [reprEffectTotalInBuffer[j]/(float(count))]

	# For simulating a number of generations sequentially
	def stepNGens(self, numGenerations):
		for i in range(numGenerations):
			self.step()
		return

	# For running a step and then updating the record.
	# CONSIDER JUST MAKING __updateRecord PUBLIC
	def recordStep(self):
		self.step()
		self.__updateRecord()
		return

	# For simulating a number of generations sequentially, recording after each
	def recordNGens(self, numGenerations):
		for i in range(numGenerations):
			self.step()
			self.__updateRecord()
		return

	# For simulating setSize*setNum generations sequentially, recording every setSize'th generation
	def recordEveryNGens(self, setSize, setNum):
		for i in range(setNum):
			self.stepNGens(setSize)
			self.__updateRecord()
		return

	def printRecord(self):
		print self.record
		return

	# Takes a filename and mutation ID
	# Writes a tab delineated file of the generation and count data for that mutation
	def writeMutation(self,filename,ID):
		outfile = open(filename, 'w')
		# outfile.write('Mutation '+str(ID)+'\n')
		outfile.write('Generation\tCount\n')
		# outfile.write(str(self.record[0][0]) + '\t' + str(self.record[2][ID][0]) + '\n')
		# outfile.write(str(self.record[1][ID][4]) + '\t' + str(1) + '\n')
		# for t in range(1,len(self.record[0])):
		for t in range(len(self.record[0])):
			outfile.write(str(self.record[0][t]) + '\t' + str(self.record[2][ID][t]) + '\n')
		outfile.close()

	# Takes a filename and inversion ID
	# Writes a tab delineated file of the generation, count, 
	#  average number of mutations in buffer, average cumulative survival,
	#  and average cumulative effect data for that inversion
	def writeInversion(self,filename,ID):
		outfile = open(filename, 'w')
		# outfile.write('Inversion '+str(ID)+'\n')
		outfile.write('Generation\tCount\tAvgNumMut\tAvgSurEff\tAvgRepEff\n')
		# outfile.write(str(self.record[0][0]) + '\t' + str(self.record[4][ID][0]) + '\t' + str(self.record[5][ID][0]) + '\t' + str(self.record[6][ID][0]) + '\t' + str(self.record[7][ID][0]) + '\n')
		# # May want to find a way to acount for the number of mutations in the inversion and their effects upon generation
		# outfile.write(str(self.record[3][ID][3]) + '\t' + str(1) + '\t' + 'NA' + '\t' + 'NA' + '\t' + 'NA' + '\n')
		# for t in range(1,len(self.record[0])):
		for t in range(len(self.record[0])):
			outfile.write(str(self.record[0][t]) + '\t' + str(self.record[4][ID][t]) + '\t' + str(self.record[5][ID][t]) + '\t' + str(self.record[6][ID][t]) + '\t' + str(self.record[7][ID][t]) + '\n')
		outfile.close()

	# Takes a filename and writes a tab delineated file of the freuency by generation and ID
	#   with generation in the first column
	# def writeAllMutFreqTable(self,filename):

	# Takes a filename and writes a tab delineated file of the freuency by generation and ID
	#   with generation in the first column
	# def writeAllInvFreqTable(self,filename):

	# Takes a filename and writes a tab delineated file of the position, effect, chromosome,
	#   and initial generation data for all mutations
	def writeMutCharTable(self,filename):
		outfile = open(filename, 'w')
		outfile.write('Position\tSurEffect\tRepEffect\tChromosome\tInitGen\n')
		for m in range(len(self.record[1])):
			line = ''
			for datum in self.record[1][m]:
				line += str(datum) + '\t'
			outfile.write(line[:-1] + '\n')
		outfile.close()

	# Takes a filename and writes a tab delineated file of the positions, chromosome,
	#   and initial generation data for all inversions
	def writeInvCharTable(self,filename):
		outfile = open(filename, 'w')
		outfile.write('Position1\tPosition2\tChromosome\tInitGen\n')
		for i in range(len(self.record[3])):
			line = ''
			for datum in self.record[3][i]:
				line += str(datum) + '\t'
			outfile.write(line[:-1] + '\n')
		outfile.close()

	# Writes a summary file for the
	def writeSummary(self,filename):
		outfile = open(filename, 'w')
		outfile.write('Parameter\tValue\n')
		outfile.write('Size\t'+str(self.size)+'\n')
		outfile.write('MutationRate\t'+str(self.mutRate)+'\n')
		outfile.write('InversionMutationRate\t'+str(self.mutRateInv)+'\n')
		outfile.write('MutationEffectOffsetSD\t'+str(self.mutEffectDiffSD)+'\n')
		outfile.write('MinimumInversionLength\t'+str(self.minInvLen)+'\n')
		outfile.write('ConversionRate\t'+str(self.conversionRate)+'\n')
		outfile.write('RecombinationRate\t'+str(self.recombRate)+'\n')
		outfile.write('EncounterNumber\t'+str(self.encounterNum)+'\n')
		outfile.write('FemaleChoiceNoiseSD\t'+str(self.choiceNoiseSD)+'\n')
		outfile.write('InversionRecordBuffer\t'+str(self.invRecBuffer)+'\n')
		outfile.close()
		return

	# Writes record to outfiles as such:
	# One summary document
	# Tab delineated table of mutation characteristics for all mutations
	# Tab delineated table of inversion characteristics for all inversions
	# Tab delineated table with generation and count data for every mutation
	# Tab delineated table with generation, count, etc. additional data for every inversion
	def writeRecordTables(self,outFilePrefix):
		self.writeSummary(outFilePrefix+'ParamSumm.txt')
		self.writeMutCharTable(outFilePrefix+'MutSumm.txt')
		self.writeInvCharTable(outFilePrefix+'InvSumm.txt')
		for mutID in range(self.__mutIDcount):
			filename = outFilePrefix+'Mut'+str(mutID)+'.txt'
			self.writeMutation(filename,mutID)
		for invID in range(self.__invIDcount):
			filename = outFilePrefix+'Inv'+str(invID)+'.txt'
			self.writeInversion(filename,invID)
		return

	# # Scratch for testing mutation data change (due to shared reference)
	# def testSharedData(self):
	# 	mutCounts = [0]*self.__mutIDcount
	# 	for indiv in self.males + self.females:
	# 		for chrom in indiv.genome:
	# 			for hom in chrom:
	# 				for mut in hom[0]:
	# 					mutCounts[mut[3]] += 1
	# 	for i in range(self.__mutIDcount):
	# 		if mutCounts[i] == 2*self.size:
	# 			# self.record[1][i] = mut
	# 			# mut[2] = 'test'
	# 			print 'Starting test for ID '+ str(i)
	# 			# print mut
	# 			# print self.record[1][i]
	# 			firstEncounter = True
	# 			for indiv in self.males + self.females:
	# 				for chrom in indiv.genome:
	# 					for hom in chrom:
	# 						for mut in hom[0]:
	# 							if mut[3] == i:
	# 								if firstEncounter:
	# 									mut[2] = 'test'
	# 									firstEncounter = False
	# 								print mut
	# 	return




