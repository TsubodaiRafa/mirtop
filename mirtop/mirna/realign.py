from Bio import pairwise2
from Bio.Seq import Seq
from collections import defaultdict

from mirtop.mirna.keys import *

class hits:

    def __init__(self):
        self.sequence = ""
        self.idseq = ""
        self.precursors = defaultdict(isomir)
        self.score = []
        self.best_hits = [] # maybe sam object?
        self.counts = 0

    def set_sequence(self, seq):
        self.sequence = seq
        self.idseq = make_id(seq)

    def set_precursor(self, precursor, isomir):
        self.precursors[precursor] = isomir

    def remove_precursor(self, precursor):
        del self.precursors[precursor]

class isomir:

    def __init__(self):
        self.t5 = []
        self.t3 = []
        self.add = []
        self.subs = []
        self.align = None
        self.cigar = None
        self.filter = "Pass"
        self.map_score = 0
        self.end = None
        self.start = None
        self.mirna = None
        self.strand = "+"

    def set_pos(self, start, l, strand = "+"):
        self.strand = strand
        self.start = start
        self.end = start + l - 1
        if strand == "-":
            self.start = start + l - 1
            self.end = start

    def formatGFF(self):
        value = ""
        subs = self.subs
        if subs:
            if subs[0] > 1 and subs[0] < 8:
                value += "iso_snp_seed,"
            elif subs[0] == 8:
                value += "iso_snp_central_offset,"
            elif subs[0] > 8 and subs[0] < 13:
                value += "iso_snp+central,"
            elif subs[0] > 12 and subs[0] < 18:
                value += "iso_snp_central_supp,"
            else:
                value += "iso_snp,"
        if self.add:
            value += "iso_add,"
        if self.t5:
            value += "iso_5p,"
        if self.t3:
            value += "iso_3p,"
        if not value:
            value += "NA,"
        return value[:-1]

    def format(self, sep="\t"):
        subs = "".join(["".join(map(str, mism)) for mism in self.subs])
        if not subs:
            subs = "0"
        add = "0" if not self.add else self.add
        return "%s%s%s%s%s%s%s" % (subs, sep, add, sep,
                                   self.t5, sep, self.t3)

    def format_id(self, sep="\t"):
        subs = ["".join(["".join([c[2], str(c[0]), c[1]]) for c in self.subs])]
        if not subs:
            subs = []
        add = [] if not self.add else ["e%s" % self.add]
        t5 = ["s%s" % self.t5] if self.t5 and self.t5 != "NA" else []
        t3 = ["%s" % self.t3] if self.t3 and self.t3 != "NA" else []
        full = t5 + subs + t3 + add
        return sep.join([f for f in full if f])

    def get_score(self, sc):
        for a in self.add:
            if a in ['A', 'T']:
                sc -= 0.25
            else:
                sc -= 0.75
        for e in self.subs:
            sc -= 1
        return sc

    def is_iso(self):
        if self.t5 or self.t3 or self.add or self.subs:
            return True
        return False

def make_id(seq):
    start = 0
    idName = ""
    for i in range(0, len(seq) + 1, 3):
        if i == 0:
            continue
        trint = seq[start:i]
        idName += NT2CODE[trint]
        start = i
    if len(seq) > i:
        dummy = "A" * (3 - (len(seq) - i))
        trint = seq[i:len(seq)]
        idName += NT2CODE["%s%s" % (trint, dummy)]
        idName += str(len(dummy))
    return idName

def align(x, y):
    """
    https://medium.com/towards-data-science/pairwise-sequence-alignment-using-biopython-d1a9d0ba861f
    """
    return pairwise2.align.globalms(x, y, 1, -1, -1, -0.5)[0]

def _add_cigar_char(counter, cache):
    if counter == 1:
        return cache
    else:
        return str(counter) + cache

def make_cigar(seq, mature):
    """
    Function that will create CIGAR string from aligment
    between read and reference sequence.
    """
    cigar = ""
    for pos in range(0,len(seq)):
        if seq[pos] == mature[pos]:
            cigar += "M"
        elif seq[pos] != mature[pos] and seq[pos] != "-" and mature[pos] != "-":
            cigar += mature[pos]
        elif seq[pos] == "-":
            cigar += "D"
        elif mature[pos] == "-":
            cigar += "I"

    cache = ""
    counter = 1
    short = ""
    for c in cigar:
        if c != cache and cache != "" and cache == "M":
            short += _add_cigar_char(counter, cache)
            counter = 1
            cache = c
        if c != "M":
            short += c
        if c == cache and c == "M":
            counter += 1
        cache = c

    if cache == "M":
        short += _add_cigar_char(counter, cache)
    return short

def cigar_correction(cigarLine, query, target):
    """Read from cigar in BAM file to define mismatches"""
    query_pos = 0
    target_pos = 0
    query_fixed = []
    target_fixed = []
    for (cigarType, cigarLength) in cigarLine:
        if cigarType == 0: #match 
            query_fixed.append(query[query_pos:query_pos+cigarLength])
            target_fixed.append(target[target_pos:target_pos+cigarLength])
            query_pos = query_pos + cigarLength
            target_pos = target_pos + cigarLength
        elif cigarType == 1: #insertions
            query_fixed.append(query[query_pos:query_pos+cigarLength])
            target_fixed.append("".join(["-"] * cigarLength))
            query_pos = query_pos + cigarLength
        elif cigarType == 2: #deletion
            target_fixed.append(target[target_pos:target_pos+cigarLength])
            query_fixed.append("".join(["-"] * cigarLength))
            target_pos = target_pos + cigarLength
    return ["".join(query_fixed), "".join(target_fixed)]

def reverse_complement(seq):
    return Seq(seq).reverse_complement()
