# Multi-Database Support

Olaf supports running multiple independent fingerprint databases via the `--db` flag. This lets you maintain separate indexes — for example, one per audio collection, client, or environment — and query against each independently.

## Usage

Pass `--db <path>` before any command to use a custom database root directory:

```bash
olaf --db /path/to/my_db store audio1.mp3 audio2.mp3
olaf --db /path/to/my_db query test.mp3
olaf --db /path/to/my_db stats
```

When `--db` is omitted, Olaf uses the default location `~/.olaf`.

The directory structure created under the given path:

```
/path/to/my_db/
  db/       # LMDB fingerprint store
  cache/    # cached fingerprint files
```

Both directories are created automatically on first use.

## Examples

### Separate databases per collection

```bash
# Index podcasts into one database
olaf --db ~/olaf_podcasts store ~/podcasts/*.mp3

# Index music into another
olaf --db ~/olaf_music store ~/music/*.mp3

# Query a clip against only the music database
olaf --db ~/olaf_music query clip.mp3

# Check stats for each
olaf --db ~/olaf_podcasts stats
olaf --db ~/olaf_music stats
```

### Scripted multi-database queries

Query the same file against several databases:

```bash
for db in ~/olaf_db_a ~/olaf_db_b ~/olaf_db_c; do
  echo "=== Querying against $db ==="
  olaf --db "$db" query test.mp3
done
```

### All commands work with --db

`--db` is a global option that works with every Olaf command:

```bash
olaf --db /tmp/test_db store file.mp3
olaf --db /tmp/test_db query file.mp3
olaf --db /tmp/test_db delete file.mp3
olaf --db /tmp/test_db stats
olaf --db /tmp/test_db clear
olaf --db /tmp/test_db dedup
```

## How it works

The Ruby wrapper (`olaf.rb`) parses `--db` and sets the `DB_FOLDER` and `CACHE_FOLDER` paths to subdirectories of the given root. When a custom path is specified, it passes the `OLAF_DB` environment variable to the C binary (`olaf_c`), which reads it in `olaf_config.c` to override the default database location.

When `--db` is not provided, `OLAF_DB` is not set and the C binary falls back to `~/.olaf/db/` as before.

## Testing

A test script is provided to verify multi-database functionality end-to-end:

```bash
python tests/test_multi_db.py --music-dir /path/to/music --creatives-dir /path/to/creatives
```

This creates 3 temporary databases, splits music files across them, stores and queries independently, and reports matches per database. All temporary databases are cleaned up on exit. See `tests/test_multi_db.py` for details.
