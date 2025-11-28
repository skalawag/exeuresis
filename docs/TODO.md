# TODO

## Feature Enhancements

### Plutarch Stephanus Pagination Display

**Status**: ✅ Implemented
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

**Implementation Summary**:
1. ✅ Updated `TextExtractor._extract_stephanus_markers()` to recognize both `unit="section"` (Plato) and `unit="stephpage"` (Plutarch)
2. ✅ Updated `TextExtractor._split_at_milestones()` to:
   - Handle both marker types when splitting text
   - Create separate text segments for each milestone (fixed bug where consecutive milestones like 1014a and 1014b were being merged into one segment)
3. ✅ Updated `TextFormatter._format_stephanus_with_context()` to display full marker when text starts with non-'a' section (e.g., [1012b])
4. ✅ Tested with Plutarch's De animae procreatione (tlg0007.tlg134) - displays [1012b], [1012c], [1014], [b], [c], [d], etc.
5. ✅ Verified backward compatibility with Plato's Euthyphro - still displays [2a], [2b], etc.
6. ✅ Added comprehensive tests in `tests/test_extractor.py`:
   - `test_extract_plutarch_stephpage_markers()` - validates Plutarch marker extraction
   - `test_stephanus_marker_types_support()` - validates both Plato and Plutarch markers work

**Modified Files**:
- `pi_grapheion/extractor.py` - Updated marker extraction logic (lines 233-260) and milestone splitting logic (lines 405-426)
- `pi_grapheion/formatter.py` - Updated pagination display logic (lines 832-875)
- `tests/test_extractor.py` - Added new tests for stephpage support (lines 161-216)
- `tests/test_stephanus_formatting.py` - Updated test expectations for non-'a' first markers
- `docs/TODO.md` - Updated status to completed

**Verification**: All 88 Plutarch works using stephpage markers now display pagination correctly.

