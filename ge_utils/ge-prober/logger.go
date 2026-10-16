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

// FormatJudgeVerdict formats the LLM judge verdict line.
func FormatJudgeVerdict(eval *SemanticEvaluation) string {
	if eval == nil {
		return ""
	}
	icon := "✅ FULFILLED"
	if !eval.Fulfilled {
		icon = "❌ UNFULFILLED"
	}
	modelStr := eval.JudgeModel
	if modelStr == "" {
		modelStr = "Vertex AI Judge"
	}

	res := fmt.Sprintf("⚖️ Judge Verdict: %s (Score: %d/5 | %s)", icon, eval.Score, modelStr)
	if eval.Reasoning != "" {
		res += fmt.Sprintf("\n   ↳ 💭 %s", eval.Reasoning)
	}
	return res
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
	SemanticEval   *SemanticEvaluation
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

// SetSemanticEval sets the judge evaluation.
func (pt *ProbeTrace) SetSemanticEval(eval *SemanticEvaluation) {
	pt.SemanticEval = eval
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

	if pt.SemanticEval != nil {
		fmt.Fprintln(w, FormatJudgeVerdict(pt.SemanticEval))
	}
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

// FormatExecutionSummary formats the end-of-run summary banner.
func FormatExecutionSummary(report ProberReport, totalDurationSec float64, outputFile string) string {
	passRate := 0.0
	sloRate := 0.0
	semanticRate := 0.0
	if report.TotalProbes > 0 {
		passRate = float64(report.FunctionalPassed) / float64(report.TotalProbes) * 100.0
		sloRate = float64(report.SLOPassed) / float64(report.TotalProbes) * 100.0
		semanticRate = float64(report.SemanticPassed) / float64(report.TotalProbes) * 100.0
	}

	var sb strings.Builder
	sb.WriteString("================================================================================\n")
	sb.WriteString("📊 TEST SUITE EXECUTION SUMMARY\n")
	sb.WriteString("================================================================================\n")
	sb.WriteString(fmt.Sprintf("Total Test Cases     : %d\n", report.TotalProbes))
	sb.WriteString(fmt.Sprintf("Functional Pass Rate : %d/%d (%.1f%%)\n", report.FunctionalPassed, report.TotalProbes, passRate))
	sb.WriteString(fmt.Sprintf("Semantic Pass Rate   : %d/%d (%.1f%%)\n", report.SemanticPassed, report.TotalProbes, semanticRate))
	sb.WriteString(fmt.Sprintf("SLO Compliance Rate  : %d/%d (%.1f%%)\n", report.SLOPassed, report.TotalProbes, sloRate))
	sb.WriteString(fmt.Sprintf("Total Run Duration   : %.2fs\n", totalDurationSec))
	if outputFile != "" {
		sb.WriteString(fmt.Sprintf("Report Exported To   : %s\n", outputFile))
	}
	sb.WriteString("================================================================================")
	return sb.String()
}

