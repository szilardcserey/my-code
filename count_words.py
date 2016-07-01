
def read_chunks(f, chunk_size=1024):
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        yield chunk

def count_words_in_chunk(chunk):
    word_list = re.split("\W+", chunk)
    tail = word_list.pop()
    return len([w for w in word_list if w]), tail

def count_words(files):
    counted_words = 0
    for fi in files:
        try:
            with open(fi, 'r') as f:
                tail = ''
                for chunk in read_chunks(f, 1):
                    number_words_in_chunk, tail = count_words_in_chunk(tail + chunk)
                    counted_words += number_words_in_chunk
        except IOError:
            print('cannot open file: %s' % fi)
    return counted_words

