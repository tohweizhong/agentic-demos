package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strings"
	"sync"
)

// FormatProbeHeader formats the probe header e.g. "[4/4] 🔎 [sharepoint] sharepoint_01".
func FormatProbeHeader(index, total int, groundingType, testCaseID string) string {
	gt := groundingType
	if gt == "" {
		gt = "generic"
	}
	return fmt.Sprintf("[%d/%d] 🔎 [%s] %s", index, total, gt, testCaseID)
}

// FormatQuery formats the query display line.
func FormatQuery(query string) string {
	return fmt.Sprintf("📜 Query: %q", query)
}

// FormatStreamDone formats the stream completion timing banner.
func FormatStreamDone(ttftMs, totalLatencyMs float64) string {
	return fmt.Sprintf("✅ Stream Done (TTFT: %.1f ms | Total: %.1f ms)", ttftMs, totalLatencyMs)
}

// FormatResponseLines splits a raw response into clean, non-empty lines for logging.
func FormatResponseLines(rawResponse string) []string {
	var lines []string
	scanner := bufio.NewScanner(strings.NewReader(rawResponse))
	for scanner.Scan() {
		line := strings.TrimRight(scanner.Text(), " \r\t")
		if strings.TrimSpace(line) != "" {
			lines = append(lines, line)
		}
	}
	return lines
}

// ProbeTrace holds formatted log lines for a single test probe execution.
type ProbeTrace struct {
	Index          int
	Total          int
	GroundingType  string
	ID             string
	Query          string
	Thoughts       []string
	Response       string
	TTFTMs         float64
	TotalLatencyMs float64
}

// NewProbeTrace creates a new trace buffer.
func NewProbeTrace(index, total int, groundingType, id, query string) *ProbeTrace {
	return &ProbeTrace{
		Index:         index,
		Total:         total,
		GroundingType: groundingType,
		ID:            id,
		Query:         query,
	}
}

// AddThought adds a thought/reasoning line to the trace.
func (pt *ProbeTrace) AddThought(thought string) {
	if strings.TrimSpace(thought) != "" {
		pt.Thoughts = append(pt.Thoughts, thought)
	}
}

// SetResponse sets the final complete response.
func (pt *ProbeTrace) SetResponse(resp string) {
	pt.Response = resp
}

// SetTimings sets the TTFT and total latency.
func (pt *ProbeTrace) SetTimings(ttftMs, totalLatencyMs float64) {
	pt.TTFTMs = ttftMs
	pt.TotalLatencyMs = totalLatencyMs
}

// EmitTo writes the formatted probe trace to an io.Writer.
func (pt *ProbeTrace) EmitTo(w io.Writer) {
	fmt.Fprintln(w, FormatProbeHeader(pt.Index, pt.Total, pt.GroundingType, pt.ID))
	fmt.Fprintln(w, FormatQuery(pt.Query))

	if len(pt.Thoughts) > 0 {
		fmt.Fprintln(w, "💭 Thought:")
		for _, thought := range pt.Thoughts {
			lines := FormatResponseLines(thought)
			for _, l := range lines {
				fmt.Fprintln(w, l)
			}
		}
	}

	if pt.Response != "" {
		fmt.Fprintln(w, "💬 Response:")
		lines := FormatResponseLines(pt.Response)
		for _, l := range lines {
			fmt.Fprintln(w, l)
		}
	}

	fmt.Fprintln(w, FormatStreamDone(pt.TTFTMs, pt.TotalLatencyMs))
}

// StreamLogger synchronizes trace printing across multiple concurrent workers.
type StreamLogger struct {
	mu      sync.Mutex
	writer  io.Writer
	verbose bool
}

// NewStreamLogger creates a new StreamLogger.
func NewStreamLogger(w io.Writer, verbose bool) *StreamLogger {
	if w == nil {
		w = os.Stdout
	}
	return &StreamLogger{
		writer:  w,
		verbose: verbose,
	}
}

// EmitTrace atomically outputs a probe trace.
func (sl *StreamLogger) EmitTrace(trace *ProbeTrace) {
	if sl == nil || !sl.verbose || trace == nil {
		return
	}
	sl.mu.Lock()
	defer sl.mu.Unlock()
	trace.EmitTo(sl.writer)
	fmt.Fprintln(sl.writer)
}
