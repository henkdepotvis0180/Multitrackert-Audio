# Known-ad reference validation for 0.5

The implementation has two separate paths:

1. **Audio:** compare a locally supplied reference with the entire recording, using
   overlapping windows and a 0.70 normalized waveform-correlation threshold. Only
   strong full-reference matches enter the existing coherence-based acoustic
   reference estimator. Unmatched time spans are copied unchanged. A reconstruction
   residual preserves all input samples across cleaned audio and the radio track.
2. **Text:** optional offline Dutch Whisper Small transcription and specific phrase
   matching. Matches are review clues in windows up to 16 seconds. Text never
   authorizes muting a region or removing a speaker. Initial short phrases have
   source links in `multitrack/ad_text.py`; this is not an exhaustive ad catalogue.

## Measured example

A user-supplied 3.864-second AH sound-logo example was mixed three times with the
real, unrelated speech fixture from the official sherpa-onnx release, at higher
radio volume with a 5 ms echo. This is a constructed mixture with known ground
truth, **not the user's real conversation recording**. User audio is not committed
or bundled in this repository.

The reproducible evaluation found all three inserted clips at 2.000, 9.864 and
17.728 seconds. Error power relative to the clean speech fell by **25.70 dB**.
Remaining error RMS was **0.141 times** clean-speech RMS. These are signal-error
measurements, not a guarantee that every word is preserved or a perceptual score.
The cleaned signal plus the removed track reconstructed the mixture within float
roundoff. A Chromium test also exercised the real upload/worker/export pipeline
with AAC video, finding all three references and decoding the radio WAV.

Reproduce with a local reference (the destination must not already exist):

```bash
python scripts/download_test_audio.py
python scripts/evaluate_ad_reference.py --reference /path/to/my-ad.mp3 --output work/ad-check
```

The evaluation writes local mixture, clean-speech ground truth, filtered audio,
removed audio and `metrics.json`. Results depend on the supplied reference.

## Negative and boundary cases

Tests cover no-match audio being left untouched, stereo reconstruction, repeated
references, the start and end of a recording, matches after 90 seconds and across
search-window boundaries. Text tests distinguish full identifying phrases from
brand names alone. Overflow tests verify that extra voices remain audible in the
residual and are not silently discarded or relabelled as two people.

## Known limits

Both Whisper Tiny and Whisper Small mis-transcribed the supplied sung slogan.
Adding the slogan as text did not fix that failure. Audio comparison worked on
this exact example, which is why the paths remain independent. The earlier video
was repeated slogan audio, not additional diverse voice examples or a meeting mix.

Different edits, performances, speed changes, long room reverberation, distortion
and speech much louder than the reference can prevent a match. The estimator can
leave radio or leak some conversation into the removed track. An unknown ad is
not covered merely because it uses a familiar brand or a familiar voice. Actual
field validation still requires representative mixed conversation recordings.

Primary sources for the short starter phrases:

- AH: https://nieuws.ah.nl/albert-heijn-start-nieuwe-campagne/
- Kruidvat: https://www.kruidvat.be/nl/winkelformule
- Lidl: https://www.lidl.nl/c/huismerken/s10023965
- Whisper/sherpa-onnx model export: https://k2-fsa.github.io/sherpa/onnx/pretrained_models/whisper/export-onnx.html
