// Olaf: Overly Lightweight Acoustic Fingerprinting
// Copyright (C) 2019-2025  Joren Six

// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

/**
 * @file olaf_stream_processor.h
 *
 * @brief Makes it more easy to process an audio stream.
 * 
 * The stream processor 
 *
 */

#ifndef OLAF_STREAM_PROCESSOR_H
#define OLAF_STREAM_PROCESSOR_H

    #include "olaf_config.h"
    #include "olaf_runner.h"
    
    /**
     * @struct Olaf_Stream_Processor
     * @brief An opaque struct with state information related to the stream processor.
     * 
     */
    typedef struct Olaf_Stream_Processor Olaf_Stream_Processor;

    /**
     * @brief      Initialize a new stream processor.
     *
     * @param      runner     The runner which determines the type of processing to take place (query, match, print,... )
     * @param[in]  raw_path   The path to the transcoded raw audio samples file 
     * @param[in]  orig_path  The original audio path to store in meta-data.
     *
     * @return     Newly created state information related to the processor.
     */
    Olaf_Stream_Processor * olaf_stream_processor_new(Olaf_Runner * runner,const char* raw_path,const char* orig_path);

    /**
     * @brief      Process a file from the first to last audio sample.
     *
     * @param      olaf_stream_processor  The olaf stream processor.
     */
    void olaf_stream_processor_process(Olaf_Stream_Processor * olaf_stream_processor);

    /**
     * @brief      Process a file once, matching the extracted fingerprints against several databases.
     *
     * The audio is decoded, transformed and turned into fingerprints a single
     * time; the resulting fingerprints are matched against each of the given
     * databases by a dedicated matcher. This avoids repeating the (database
     * independent) fingerprint extraction once per database. Results for every
     * database are printed in the same format as a single-database query.
     *
     * @param      olaf_stream_processor  The olaf stream processor (created in OLAF_RUNNER_MODE_QUERY_MULTI).
     * @param      dbs                    An array of open, read-only databases.
     * @param[in]  db_count               The number of databases in the array.
     */
    void olaf_stream_processor_process_multi(Olaf_Stream_Processor * olaf_stream_processor, Olaf_DB ** dbs, size_t db_count);

    /**
     * @brief      Free up memory and release resources.
     *
     * @param      olaf_stream_processor  The olaf stream processor.
     */
    void olaf_stream_processor_destroy(Olaf_Stream_Processor * olaf_stream_processor);

#endif // OLAF_STREAM_PROCESSOR_H
