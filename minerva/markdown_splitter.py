from enum import Enum
from typing import List, Generator

FORMATTING_SEQUENCES = {"*", "**", "***", "_", "__", "~~", "||"}
CODE_BLOCK_SEQUENCES = {"`", "``", "```"}
ALL_SEQUENCES = FORMATTING_SEQUENCES | CODE_BLOCK_SEQUENCES
MAX_FORMATTING_SEQUENCE_LENGTH = max(len(seq) for seq in ALL_SEQUENCES)


class SplitCandidates(Enum):
  SPACE = 1
  NEWLINE = 2
  LAST_CHAR = 3


# Order of preference for splitting
SPLIT_CANDIDATES_PREFRENCE = [
  SplitCandidates.NEWLINE,
  SplitCandidates.SPACE,
  SplitCandidates.LAST_CHAR,
]


class SplitCandidateInfo:
  last_seen: int
  active_sequences: List[str]
  active_sequences_length: int

  def __init__(self):
    self.last_seen = None
    self.active_sequences = []
    self.active_sequences_length = 0

  def process_sequence(self, seq: str, is_in_code_block: bool):
    """Process `seq`, update `self.active_sequences` and `self.active_sequences_length`,
    and return whether we are in a code block after processing `seq`.
    """

    if is_in_code_block:
      if seq == self.active_sequences[-1]:
        last_seq = self.active_sequences.pop()
        self.active_sequences_length -= len(last_seq)
        return False
      return True
    elif seq in CODE_BLOCK_SEQUENCES:
      self.active_sequences.append(seq)
      self.active_sequences_length += len(seq)
      return True
    else:
      for k in range(len(self.active_sequences) - 1, -1, -1):
        if seq == self.active_sequences[k]:
          sequences_being_removed = self.active_sequences[k:]
          self.active_sequences = self.active_sequences[:k]
          self.active_sequences_length -= sum(len(seq) for seq in sequences_being_removed)
          return False
      self.active_sequences.append(seq)
      self.active_sequences_length += len(seq)
      return False

  def copy_from(self, other):
    self.last_seen = other.last_seen
    self.active_sequences = other.active_sequences.copy()
    self.active_sequences_length = other.active_sequences_length


def split_markdown(markdown: str, max_chunk_size: int) -> Generator[str, None, None]:
  """Naive markdown splitter that splits long messages in chunks
  preserving the markdown formatting tags supported by Discord.
  """

  if max_chunk_size <= MAX_FORMATTING_SEQUENCE_LENGTH:
    raise ValueError(f"max_chunk_size must be greater than {MAX_FORMATTING_SEQUENCE_LENGTH}")

  if len(markdown) <= max_chunk_size:
    # No need to split if the message is already short enough
    yield markdown
    return

  split_candidates = {
      SplitCandidates.SPACE: SplitCandidateInfo(),
      SplitCandidates.NEWLINE: SplitCandidateInfo(),
      SplitCandidates.LAST_CHAR: SplitCandidateInfo(),
  }
  is_in_code_block = False

  chunk_start_from, chunk_char_count, chunk_prefix = 0, 0, ""

  def split_chunk():
    for split_variant in SPLIT_CANDIDATES_PREFRENCE:
      split_candidate = split_candidates[split_variant]
      if split_candidate.last_seen is None:
        continue
      chunk_end = split_candidate.last_seen + \
        (1 if split_variant == SplitCandidates.LAST_CHAR else 0)
      chunk = chunk_prefix + markdown[chunk_start_from:chunk_end] + \
        "".join(reversed(split_candidate.active_sequences))

      next_chunk_prefix = "".join(split_candidate.active_sequences)
      next_chunk_char_count = len(next_chunk_prefix)
      next_chunk_start_from = chunk_end + (0 if split_variant == SplitCandidates.LAST_CHAR else 1)

      split_candidates[SplitCandidates.NEWLINE] = SplitCandidateInfo()
      split_candidates[SplitCandidates.SPACE] = SplitCandidateInfo()
      return chunk, next_chunk_start_from, next_chunk_char_count, next_chunk_prefix

  i = 0
  while i < len(markdown):
    for j in range(MAX_FORMATTING_SEQUENCE_LENGTH, 0, -1):
      seq = markdown[i:i + j]
      if seq in ALL_SEQUENCES:
        last_char_split_candidate_len = chunk_char_count + \
          split_candidates[SplitCandidates.LAST_CHAR].active_sequences_length + \
          len(seq)
        if last_char_split_candidate_len >= max_chunk_size:
          next_chunk, chunk_start_from, chunk_char_count, chunk_prefix = split_chunk()
          yield next_chunk
        is_in_code_block = split_candidates[SplitCandidates.LAST_CHAR].process_sequence(
            seq, is_in_code_block)
        i += len(seq)
        chunk_char_count += len(seq)
        split_candidates[SplitCandidates.LAST_CHAR].last_seen = i - 1
        break

    split_candidates[SplitCandidates.LAST_CHAR].last_seen = i
    chunk_char_count += 1
    if markdown[i] == "\n":
      split_candidates[SplitCandidates.NEWLINE].copy_from(
          split_candidates[SplitCandidates.LAST_CHAR])
    elif markdown[i] == " ":
      split_candidates[SplitCandidates.SPACE].copy_from(split_candidates[SplitCandidates.LAST_CHAR])

    last_char_split_candidate_len = chunk_char_count + \
      split_candidates[SplitCandidates.LAST_CHAR].active_sequences_length
    if last_char_split_candidate_len == max_chunk_size:
      next_chunk, chunk_start_from, chunk_char_count, chunk_prefix = split_chunk()
      yield next_chunk

    i += 1

  if chunk_start_from < len(markdown):
    yield chunk_prefix + markdown[chunk_start_from:]
