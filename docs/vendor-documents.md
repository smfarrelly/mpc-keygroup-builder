# Vendor document cache

Official MIDI implementation charts are valuable evidence for declarative
controller maps, but vendor PDFs are not automatically open-source just because
they are downloadable.

Korg's download terms state that its manuals and product literature are
copyrighted, permit one personal noncommercial copy, and prohibit duplication
or posting online. Therefore this repository stores canonical URLs, expected
metadata, and checksums in `references/vendor-documents.toml`; it does not
commit the PDFs.

## List the tracked references

```bash
mpc-reference-cache list
```

The initial set covers the official Volca Bass, Volca Keys, Volca Drum
single-channel, and Volca Drum split-channel MIDI implementation charts.

## Fetch personal working copies

Choose an ignored or external directory:

```bash
mpc-reference-cache --cache-dir "/absolute/path/to/Reference Documents/Korg" \
  fetch
```

The command downloads only HTTPS URLs in the manifest, writes atomically, and
records SHA-256 evidence. It never writes vendor documents into a Git-tracked
location by default. Cached documents and `index.json` must be regular files;
symbolic links are rejected before hashing or writing so the personal cache
cannot silently read or replace a file elsewhere.

## Verify copies later

```bash
mpc-reference-cache --cache-dir "/absolute/path/to/Reference Documents/Korg" \
  verify
```

A changed hash is a review signal: compare the new upstream document before
updating declarative device facts. The official upstream URL remains the
authority.

The MIDI channel and CC facts in `midi/devices/` are independently maintained
structured data with source attribution. Keep facts concise, cite the relevant
official chart, and do not copy the PDF's expressive text or graphics into the
repository.
