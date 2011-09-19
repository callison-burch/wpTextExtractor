#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

__author__ = 'Andreas Eisele <eisele@dfki.de>'
__created__ = "Tue Jan 26 21:41:40 2010"

'''
extract clear text from wikipedia articles
'''


import re
import mwlib
from mwlib.refine.compat import parse_txt
from mwlib.refine import core 
from mwlib.parser import nodes


# map all node types to the empty string
nodeTypes = [getattr(nodes,d) for d in dir(nodes)]
nodeTypes = [x for x in nodeTypes if type(x)==type]
node2markup = dict((n,'') for n in nodeTypes)
# except for those
node2markup[nodes.Section]='<s>'
node2markup[nodes.Item]='<i>'

# obsolete; mwlib takes care of them
def wikitableline2text(line, separator):
	barpos = line.find(separator)
	if barpos == -1:
		# if the bar seperator is not found, then the whole line is text
		return line
	else:
		if not line[barpos:].startswith(separator+separator):
			# if a single bar separator is in the line, then the preceding text is parameter and should be removed
			line = line[barpos+1:]
		# remove cell seperator (||)
		return re.sub('\|\||!!', '\n', line)

# obsolete; mwlib takes care of them
def wikitable2text(wiki):
	result = ''
	for line in wiki.group(0).split('\n'):
		if line.startswith('{|') or line.startswith('|-') or line.startswith('|}'):
			pass
		elif line.startswith('|+'):
			result += wikitableline2text(line[2:], '|') + '\n'
		elif line.startswith('|') or line.startswith('!'):
			result += wikitableline2text(line[1:], line[0]) + '\n'
	return result

def wikitemplate2text(wiki):
	# remove double brackets
	wiki = wiki.group(0)[2:-2]
	lower = wiki.lower()
	# save languages and dates
	if lower.startswith('lang') or lower.startswith('date') or lower.startswith('ipa') or lower.startswith('pron') or lower.startswith('nihongo'):
		barpos = wiki.find('|')
		if barpos != -1:
			return wiki.split('|')[1]
	return ''

def wiki2sentences(wiki, sent_detector, withTags=True, withCitations=False):
	# save the dates (made obsolete by introduction of wikitemplate2text)
	#wiki = re.sub('{{date\|([^{}]*?)}}', r'\1',  wiki)

	citations = []
	# repeat since everything can be nested
	oldLen = 1E10
	while len(wiki) < oldLen:
		oldLen = len(wiki)
		# eliminates html comments. e.g. <--This is a comment-->
		wiki = re.sub('<!--.*?-->', '', wiki)

		# eliminate wiki tables
		# commented out because mwlib takes care of them
		#wiki = re.sub('{\|[^{}]*?\|}', wikitable2text, wiki)
		
		# save citations
		citations.extend(re.findall(r'\{\{cite[^{}]*\}\}', wiki, re.IGNORECASE))
		citations.extend(re.findall(r'\{\{citation[^{}]*\}\}', wiki, re.IGNORECASE))

		# eliminate wiki templates. e.g. {{date}}
		wiki = re.sub(r'\{\{[^\{\}]*\}\}', wikitemplate2text, wiki)
		# eliminate refrence tags. e.g. <ref>text</ref>
		wiki = re.sub(r'<ref[^/>]*?>[^<]*?</ref>', '', wiki)
		# eliminate html tags. e.g. <ref name="My Life"/>
		wiki = re.sub(r'</?[A-Za-z][^>]*?>', '', wiki)
	
	# remove angle brackets
	# mwlib restores the changes, so do nothing.
	#wiki = re.sub('<', '&lt;', wiki)
	#wiki = re.sub('>', '&gt;', wiki)
	#print wiki.encode('utf-8')

	tree = parse_txt(wiki)
	text = tree2string(tree)
	lines = cleanup(text).split('\n')
	sentences = []
	tags = []
	for line in lines:
		if line.startswith('<s>'):
			sentences.append(line[3:].strip())
			tags.append('Section')
		elif line.startswith('<i>'):
			newSentences = sent_detector(line[3:].strip())
			sentences += newSentences
			tags += ['Item-Sentence']*(len(newSentences)-1)
			tags.append('Item-LastSentence')
		else:
			newSentences = sent_detector(line.strip())
			sentences += newSentences
			tags += ['Sentence']*(len(newSentences)-1)
			tags.append('LastSentence')
	if withTags:
		if withCitations:
			return sentences,tags,citations
		else:
			return sentences,tags
	else:
		if withCitations:
			return sentences,citations
		else:
			return sentences



def tree2string(tree,trace=False):
	snippets = []
	_tree2string(tree,snippets,trace)
	return ''.join(snippets)


def _tree2string(tree,snippets,trace,level=0):
	snippets.append(node2markup[type(tree)])
	if trace: print '  '*level,type(tree)
	try:
		if type(tree)==nodes.ArticleLink:
			if not tree.children:
				if tree.text:
					snippets.append(tree.text)
				else:
					snippets.append(tree.target)
				if trace: 
					print '  '*level,'ArticleLink: children:',len(tree.children)
					print '  '*level,'target',tree.target.encode('utf-8')
					print '  '*level,'text:',tree.text.encode('utf-8')
				return
		elif type(tree)==nodes.TagNode:
			return
		elif type(tree)==nodes.ImageLink:
			return
		elif tree.text:
			if trace: print '  '*level,'text:',tree.text.encode('utf-8')
			snippets.append(tree.text)
	except AttributeError: pass
	try:
		for node in tree.children:
			_tree2string(node,snippets,trace,level+1)
	except AttributeError: pass


def cleanup(text):
	# little hack to change the order of 
	text = text.replace('."','".')
	
	#strip empty lines
	text = [x.strip() for x in text.split('\n')]
	text = [x for x in text if x and x not in '<i><s>']
	text = '\n'.join(text)

	return text


