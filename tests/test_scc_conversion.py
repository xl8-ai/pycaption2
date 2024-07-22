import pytest

from pycaption import (
    SCCReader,
    SCCWriter,
    SRTReader,
    SRTWriter,
    DFXPWriter,
    WebVTTWriter,
)

from pycaption.scc import _SccTimeTranslator
from tests.mixins import CaptionSetTestingMixIn

# This is quite fuzzy at the moment.
TOLERANCE_MICROSECONDS = 600 * 1000


class TestSRTtoSCCtoSRT(CaptionSetTestingMixIn):
    def _test_srt_to_scc_to_srt_conversion(self, srt_captions):
        captions_1 = SRTReader().read(srt_captions)
        scc_results = SCCWriter().write(captions_1)
        scc_captions = SCCReader().read(scc_results)
        srt_results = SRTWriter().write(scc_captions)
        captions_2 = SRTReader().read(srt_results)
        self.assert_captionset_almost_equals(captions_1, captions_2, TOLERANCE_MICROSECONDS)

    def test_srt_to_scc_to_srt_conversion(self, sample_srt_ascii):
        self._test_srt_to_scc_to_srt_conversion(sample_srt_ascii)

    @staticmethod
    def timecode_to_frame(timestamp: str) -> int:
        values = [int(value) for value in timestamp.split(":")]
        return (values[0] * 3600 + values[1] * 60 + values[2]) * 30 + values[3]

    def test_timecode_overrun_conversion(self, sample_srt_for_scc_overrun):
        caption = SRTReader().read(sample_srt_for_scc_overrun)

        scc_results = SCCWriter().write(caption)
        scc_captions = SCCReader().read(scc_results)
        self.assert_captionset_almost_equals(caption, scc_captions, TOLERANCE_MICROSECONDS)
        code_starts = [self.timecode_to_frame(line.split()[0]) for line in scc_results.splitlines()[1:] if line.strip()]
        code_length = [len(line.split()) - 1 for line in scc_results.splitlines()[1:] if line.strip()]
        no_overrun = [
            start + length <= next_start for start, next_start, length in zip(code_starts, code_starts[1:], code_length)
        ]
        timecodes = [
            (round(caption.start / 1001), round(caption.end / 1001)) for caption in scc_captions.get_captions("en-US")
        ]
        # Keeps the original timestamps, but overrun happens.
        assert not all(no_overrun)
        assert timecodes == [(5000, 5500), (10000, 10500), (10500, 15000)]

        scc_results = SCCWriter(min_duration_frames=1).write(caption)
        scc_captions = SCCReader().read(scc_results)
        code_starts = [self.timecode_to_frame(line.split()[0]) for line in scc_results.splitlines()[1:] if line.strip()]
        code_length = [len(line.split()) - 1 for line in scc_results.splitlines()[1:] if line.strip()]
        no_overrun = [
            start + length <= next_start for start, next_start, length in zip(code_starts, code_starts[1:], code_length)
        ]
        timecodes = [
            (round(caption.start / 1001), round(caption.end / 1001)) for caption in scc_captions.get_captions("en-US")
        ]
        # Pushed the third caption so it can fit the third caption cordwords.
        assert all(no_overrun)
        assert timecodes == [(5000, 5500), (10000, 11133), (11133, 15000)]

        scc_results = SCCWriter(min_duration_frames=60).write(caption)
        scc_captions = SCCReader().read(scc_results)
        code_starts = [self.timecode_to_frame(line.split()[0]) for line in scc_results.splitlines()[1:] if line.strip()]
        code_length = [len(line.split()) - 1 for line in scc_results.splitlines()[1:] if line.strip()]
        no_overrun = [
            start + length <= next_start for start, next_start, length in zip(code_starts, code_starts[1:], code_length)
        ]
        timecodes = [
            (round(caption.start / 1001), round(caption.end / 1001)) for caption in scc_captions.get_captions("en-US")
        ]
        # Enforced 60 frames (2s after ndf adjusted) minimum duration.
        assert all(no_overrun)
        assert timecodes == [(5000, 7000), (10000, 12000), (12000, 15000)]


# The following test fails -- maybe a bug with SCCReader
#    def test_srt_to_srt_unicode_conversion(self):
#        self._test_srt_to_scc_to_srt_conversion(SAMPLE_SRT_UNICODE)


class TestSCCtoDFXP:
    def test_scc_to_dfxp(self, sample_dfxp_from_scc_output, sample_scc_multiple_positioning):
        caption_set = SCCReader().read(sample_scc_multiple_positioning)
        dfxp = DFXPWriter(relativize=False, fit_to_screen=False).write(caption_set)

        assert sample_dfxp_from_scc_output == dfxp

    @pytest.mark.skip()
    def test_dfxp_is_valid_xml_when_scc_source_has_weird_italic_commands(
        self, sample_dfxp_with_properly_closing_spans_output, sample_scc_created_dfxp_with_wrongly_closing_spans
    ):
        caption_set = SCCReader().read(sample_scc_created_dfxp_with_wrongly_closing_spans)

        dfxp = DFXPWriter().write(caption_set)

        assert dfxp == sample_dfxp_with_properly_closing_spans_output

    def test_dfxp_is_valid_xml_when_scc_source_has_ampersand_character(
        self, sample_dfxp_with_ampersand_character, sample_scc_with_ampersand_character
    ):
        caption_set = SCCReader().read(sample_scc_with_ampersand_character)

        dfxp = DFXPWriter().write(caption_set)

        assert dfxp == sample_dfxp_with_ampersand_character


class TestSCCToWebVTT:
    def test_webvtt_newlines_are_properly_rendered(
        self, sample_webvtt_from_scc_properly_writes_newlines_output, scc_that_generates_webvtt_with_proper_newlines
    ):
        caption_set = SCCReader().read(scc_that_generates_webvtt_with_proper_newlines)
        webvtt = WebVTTWriter().write(caption_set)

        assert webvtt == sample_webvtt_from_scc_properly_writes_newlines_output
