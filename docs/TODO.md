# TODO

## Feature Enhancements

### Plutarch Stephanus Pagination Display

**Status**: Not implemented
**Priority**: Medium

**Problem**:
Plutarch texts that use Stephanus pagination (unit="stephpage") currently don't display those page markers in the extract output, unlike Plato texts which show [327a], [327b], etc.

**Example**:
- Plato's Euthyphro shows: `[2a] ΕΥΘ. τί νεώτερον...`
- Plutarch's De animae procreatione (tlg0007.tlg134) shows no markers, even though the XML contains `<milestone unit="stephpage" n="1012b"/>`

**Affected Works**:
- 88 Plutarch works use stephpage markers
- 12 use stephpage as their primary pagination system
- Examples: tlg0007.tlg134 [1012-1030], tlg0007.tlg068 [14-37]

**Implementation Notes**:
1. Update `TextExtractor.get_dialogue_text()` to recognize `unit="stephpage"` in addition to `unit="section"`
2. Test with Plutarch works that have stephpage markers
3. Ensure backward compatibility with Plato texts (unit="section")
4. Update tests to cover both pagination types

**Related Code**:
- `pi_grapheion/extractor.py` - Stephanus marker extraction
- `pi_grapheion/catalog.py` - Already updated to show page ranges in list-works
- `pi_grapheion/formatter.py` - May need updates for Stephanus marker display

**Reference Issue**: Discovered during implementation of page range display feature
