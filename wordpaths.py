###############################################################################
# author: Szilard Cserey
# email:  szilard.cserey@gmail.com
# This application takes as input the path to a dictionary file
# /usr/share/dict/words, a start word and an end word and print out at least
# one path from start to end or indicates if there is no possible path
#
# python wordpaths.py /usr/share/dict/words cool fund
###############################################################################

import copy
import random
import sys
import os
import argparse

class ArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('ERROR: %s\n' % message)
        self.print_help()
        sys.exit(2)

class WordPaths:

    def __init__(self, word_list, start_word, end_word):
        self.word_list = word_list
        self.start_word = start_word
        self.end_word = end_word
        self._chain = [self.start_word]
        self.pos_char_list = []
        self.inner_loop_limit = 100
        self.outer_loop_limit = 1000

    def del_all_pos(self, position):
        candidates = []
        for (pos, char) in self.pos_char_list:
            if pos == position:
               candidates.append((pos, char))
        for (pos, char) in candidates:
            del self.pos_char_list[self.pos_char_list.index((pos, char))]

    def fill_pos_char_list(self):
        self.pos_char_list = []
        pos_list = range(0, len(self.start_word))
        matching = []
        for i in pos_list:
            if self.start_word[i] == self.end_word[i]:
                matching.append(i)

        pos_list = list(set(pos_list) - set(matching))

        for i in pos_list:
            for j in range(ord('a'), ord('z') + 1):
                self.pos_char_list.append((i,j))

    def find(self, outer_progress):
        word = self._chain[-1]
        if word == self.end_word:
            return True
        else:
            tmp_pos_char_list = copy.deepcopy(self.pos_char_list)
            tries = 0
            candidate_found = False
            while not candidate_found and tries < self.inner_loop_limit:
                inner_progress = (tries * 100) / self.inner_loop_limit
                print '%4s' % outer_progress, '%', \
                      '\t%4s' % inner_progress, '%\r',
                if tmp_pos_char_list:
                    random.shuffle(tmp_pos_char_list)
                    pos, char = random.choice(tmp_pos_char_list)
                else:
                    break
                if chr(char) != word[pos]:
                    candidate = word[:pos] + chr(char) + word[pos + 1:]
                    if (candidate in self.word_list
                        and candidate not in self._chain):
                        del tmp_pos_char_list[
                            tmp_pos_char_list.index((pos, char))]
                        if candidate[pos] == self.end_word[pos]:
                            self.del_all_pos(pos)
                        self._chain.append(candidate)
                        candidate_found = True
                tries += 1

    def run(self):
        counter = 0
        unsuccess = 0
        end_word_reached = False
        self.fill_pos_char_list()
        while not end_word_reached and counter < self.outer_loop_limit:
            outer_progress = (counter * 100) / self.outer_loop_limit
            prev_chain_len = len(self._chain)
            end_word_reached = self.find(outer_progress)
            random.shuffle(self.pos_char_list)
            counter += 1
            if len(self._chain) == prev_chain_len:
                unsuccess += 1
            else:
                unsuccess = 0

            '''
            if unsuccess == self.inner_loop_limit:
                counter -= self.inner_loop_limit
                self._chain = [self.start_word]
                self.fill_pos_char_list()
            '''
        return end_word_reached

    @property
    def chain(self):
        return self._chain



def parse_arguments():
    parser = ArgParser(prog='python %s' % __file__)
    parser.add_argument('dict_file', action='store', help='Dictionary File')
    parser.add_argument('start_word', action='store', help='Start word')
    parser.add_argument('end_word', action='store', help='End word')
    args = parser.parse_args()
    if not os.path.isfile(args.dict_file):
        print ('Dictionary file %s does not exist!' % args.dict_file)
        sys.exit(1)

    with open(args.dict_file) as f:
        word_list = [d.strip() for d in f.read().splitlines()]

    if len(args.start_word) != len(args.end_word):
        print ('start word: %s end word: %s must have the same length!'
               % (args.start_word, args.end_word))
        sys.exit(1)
    if args.start_word not in word_list:
        print 'start word: %s not in dictionary!' % args.start_word
        sys.exit(1)
    if args.end_word not in word_list:
        print 'end word: %s not in dictionary!' % args.end_word
        sys.exit(1)

    return word_list, args.start_word, args.end_word

def main():

    word_list, start_word, end_word = parse_arguments()
    wp = WordPaths(word_list, start_word, end_word)
    end_word_reached = wp.run()

    if end_word_reached:
        print '%4s' % 100,'%'
        print 'Success! chain: %s' % wp.chain
    else:
        print 'No path! chain: %s' % wp.chain

if __name__ == '__main__':
    main()