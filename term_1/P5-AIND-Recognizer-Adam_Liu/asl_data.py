import os
import numpy  as np
import pandas as pd


"""
	American Sign Language database drawn from the RWTH-BOSTON-104 frame positional data

	This class has been designed to provide a convenient interface for individual word data for students in the Udacity AI Nanodegree Program.

	For example, to instantiate and load train/test files using a feature_method 
	definition named features, the following snippet may be used:
		asl = AslDb()
		asl.build_training(tr_file, features)
		asl.build_test(tst_file, features)

	Reference for the original ASL data:
	http://www-i6.informatik.rwth-aachen.de/~dreuw/database-rwth-boston-104.php
	The sentences provided in the data have been segmented into isolated words for this database
"""
class AslDb(object):

	"""
		loads ASL database from csv files with hand position information by frame, and speaker information

		:param hands_fn: str
			filename of hand position csv data with expected format:
				video, frame, left-x, left-y, right-x, right-y, nose-x, nose-y

		:param speakers_fn:
			filename of video speaker csv mapping with expected format:
				video, speaker

		Instance variables:
			df: pandas dataframe
				snippit example:
						 left-x  left-y  right-x  right-y  nose-x  nose-y  speaker
			video frame
			98    0         149     181      170      175     161      62  woman-1
				  1         149     181      170      175     161      62  woman-1
				  2         149     181      170      175     161      62  woman-1
	"""
	def __init__(self,
				 hands_fn=os.path.join('data', 'hands_condensed.csv'),
				 speakers_fn=os.path.join('data', 'speaker.csv')):

		self.df = pd.read_csv(hands_fn).merge(pd.read_csv(speakers_fn),on='video')
		self.df.set_index(['video','frame'], inplace=True)


	"""
		wrapper creates sequence data objects for training words suitable for hmmlearn library

		:param feature_list: list of str label names
		:param csvfilename: str

		:return: WordsData object
			dictionary of lists of feature list sequence lists for each word
				{'FRANK': [[[87, 225], [87, 225], ...], [[88, 219], [88, 219], ...]]]}
	"""
	def build_training(self, feature_list, csvfilename =os.path.join('data', 'train_words.csv')):
		return WordsData(self, csvfilename, feature_list)


	"""
		wrapper creates sequence data objects for individual test word items suitable for hmmlearn library

		:param feature_method: Feature function
		:param csvfile: str
		:return: SinglesData object
			dictionary of lists of feature list sequence lists for each indexed
				{3: [[[87, 225], [87, 225], ...]]]}
	"""
	def build_test(self, feature_method, csvfile=os.path.join('data', 'test_words.csv')):
		return SinglesData(self, csvfile, feature_method)



"""
	class provides loading and getters for ASL data suitable for use with hmmlearn library
"""
class WordsData(object):

	"""
		loads training data sequences suitable for use with hmmlearn library based on feature_method chosen

		:param asl: ASLdata object
		:param csvfile: str
			filename of csv file containing word training start and end frame data with expected format:
				video,speaker,word,startframe,endframe
		:param feature_list: list of str feature labels
	"""
	def __init__(self, asl:AslDb, csvfile:str, feature_list:list):

		self._data = self._load_data(asl, csvfile, feature_list)
		self.num_items = len(self._data)
		self.words = list(self._data.keys())
		self._hmm_data = create_hmmlearn_data(self._data)


	"""
		Consolidates sequenced feature data into a dictionary of words

		:param asl: ASLdata object
		:param filename: str
			filename of csv file containing word training data
		:param feature_list: list of str

		:return: dict
	"""
	def _load_data(self, asl, filename, feature_list):

		tr_df = pd.read_csv(filename)
		dict = {}

		for i in range(len(tr_df)):

			word  = tr_df.ix[i, 'word']
			video = tr_df.ix[i, 'video']
			new_sequence = [] # list of sample lists for a sequence

			for frame in range(tr_df.ix[i,'startframe'], tr_df.ix[i,'endframe']+1):

				vid_frame = video, frame
				sample = [asl.df.ix[vid_frame][f] for f in feature_list]

				if len(sample) > 0:  # dont add if not found
					new_sequence.append(sample)

			if word in dict:
				dict[word].append(new_sequence) # list of sequences
			else:
				dict[word] = [new_sequence]

		return dict


	"""
		getter for entire db of words as series of sequences of feature lists for each frame

		:return: dict
			dictionary of lists of feature list sequence lists for each word
				{'FRANK': [[[87, 225], [87, 225], ...], [[88, 219], [88, 219], ...]]],
				...}
	"""
	def get_all_sequences(self):
		return self._data


	"""
		getter for entire db of words as (X, lengths) tuple for use with hmmlearn library

		:return: dict
			dictionary of (X, lengths) tuple, where X is a numpy array of feature lists and lengths is
			a list of lengths of sequences within X
				{'FRANK': (array([[ 87, 225],[ 87, 225], ...  [ 87, 225,  62, 127], [ 87, 225,  65, 128]]), [14, 18]),
				...}
	"""
	def get_all_Xlengths(self):
		return self._hmm_data


	"""
		getter for single word series of sequences of feature lists for each frame

		:param word: str
		:return: list
			lists of feature list sequence lists for given word
				[[[87, 225], [87, 225], ...], [[88, 219], [88, 219], ...]]]
	"""
	def get_word_sequences(self, word:str):
		return self._data[word]


	"""
		getter for single word (X, lengths) tuple for use with hmmlearn library

		:param word:
		:return: (list, list)
			(X, lengths) tuple, where X is a numpy array of feature lists and lengths is
			a list of lengths of sequences within X
				(array([[ 87, 225],[ 87, 225], ...  [ 87, 225,  62, 127], [ 87, 225,  65, 128]]), [14, 18])
	"""
	def get_word_Xlengths(self, word:str):
		return self._hmm_data[word]



"""
	class provides loading and getters for ASL data suitable for use with hmmlearn library
"""
class SinglesData(object):

	"""
		loads training data sequences suitable for use with hmmlearn library based on feature_method chosen

		:param asl: ASLdata object
		:param csvfile: str
			filename of csv file containing word training start and end frame data with expected format:
				video,speaker,word,startframe,endframe
		:param feature_list: list str of feature labels
	"""
	def __init__(self, asl:AslDb, csvfile:str, feature_list):

		self.df = pd.read_csv(csvfile)
		self.wordlist = list(self.df['word'])
		self.sentences_index  = self._load_sentence_word_indices()
		self._data = self._load_data(asl, feature_list)
		self._hmm_data = create_hmmlearn_data(self._data)
		self.num_items = len(self._data)
		self.num_sentences = len(self.sentences_index)


	"""
		Consolidates sequenced feature data into a dictionary of words and creates answer list of words in order
		of index used for dictionary keys

		:param asl: ASLdata object
		:param filename: str
			filename of csv file containing word training data
		:param feature_method: Feature function

		:return: dict
	"""
	# def _load_data(self, asl, filename, feature_method):
	def _load_data(self, asl, feature_list):

		dict = {}
		# for each word indexed in the DataFrame
		for i in range(len(self.df)):
			video = self.df.ix[i,'video']
			new_sequence = [] # list of sample dictionaries for a sequence
			for frame in range(self.df.ix[i,'startframe'], self.df.ix[i,'endframe']+1):
				vid_frame = video, frame
				sample = [asl.df.ix[vid_frame][f] for f in feature_list]
				if len(sample) > 0:  # dont add if not found
					new_sequence.append(sample)
			if i in dict:
				dict[i].append(new_sequence) # list of sequences
			else:
				dict[i] = [new_sequence]
		return dict


	"""
		create dict of video sentence numbers with list of word indices as values

		:return: dict
			{v0: [i0, i1, i2], v1: [i0, i1, i2], ... ,}
			where v# is video number and i# is index to wordlist,
			ordered by sentence structure
	"""
	def _load_sentence_word_indices(self):
		working_df = self.df.copy()
		working_df['idx'] = working_df.index
		working_df.sort_values(by='startframe', inplace=True)
		p = working_df.pivot('video', 'startframe', 'idx')
		p.fillna(-1, inplace=True)
		p = p.transpose()
		dict = {}
		for v in p:
			dict[v] = [int(i) for i in p[v] if i>=0]
		return dict


	"""
		getter for entire db of items as series of sequences of feature lists for each frame

		:return: dict
			dictionary of lists of feature list sequence lists for each indexed item
				{3: [[[87, 225], [87, 225], ...], [[88, 219], [88, 219], ...]]],
				...}
	"""
	def get_all_sequences(self):
		return self._data


	"""
		getter for entire db of items as (X, lengths) tuple for use with hmmlearn library

		:return: dict
			dictionary of (X, lengths) tuple, where X is a numpy array of feature lists and lengths is
			a list of lengths of sequences within X; should always have only one item in lengths
				{3: (array([[ 87, 225],[ 87, 225], ...  [ 87, 225,  62, 127], [ 87, 225,  65, 128]]), [14]),
				...}
	"""
	def get_all_Xlengths(self):
		return self._hmm_data


	"""
		getter for single item series of sequences of feature lists for each frame

		:param word: str
		:return: list
			lists of feature list sequence lists for given word
				[[[87, 225], [87, 225], ...]]]
	"""
	def get_item_sequences(self, item:int):
		return self._data[item]


	"""
		getter for single item (X, lengths) tuple for use with hmmlearn library

		:param word:
		:return: (list, list)
			(X, lengths) tuple, where X is a numpy array of feature lists and lengths is
			a list of lengths of sequences within X; lengths should always contain one item
				(array([[ 87, 225],[ 87, 225], ...  [ 87, 225,  62, 127], [ 87, 225,  65, 128]]), [14])
	"""
	def get_item_Xlengths(self, item:int):
		return self._hmm_data[item]



'''
	concatenates sequences and return tuple of the new list and lengths
	:param sequences:
	:return: (list, list)
'''
def combine_sequences(sequences):
	sequence_cat = []
	sequence_lengths = []
	# print("num of sequences in {} = {}".format(key, len(sequences)))
	for sequence in sequences:
		sequence_cat += sequence
		num_frames = len(sequence)
		sequence_lengths.append(num_frames)
	return sequence_cat, sequence_lengths


def create_hmmlearn_data(dict):
	seq_len_dict = {}
	for key in dict:
		sequences = dict[key]
		sequence_cat, sequence_lengths = combine_sequences(sequences)
		seq_len_dict[key] = np.array(sequence_cat), sequence_lengths
	return seq_len_dict


if __name__ == '__main__':
	asl= AslDb()
	print(asl.df.ix[98, 1])


