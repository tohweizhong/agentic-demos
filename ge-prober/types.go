package main

import (
	"time"
)

// Config represents runtime configuration parameters for ge-prober.
type Config struct {
	ProjectID      string   `json:"project_id"`
	Location       string   `json:"location"`
	EngineID       string   `json:"engine_id"`
	AssistantID    string   `json:"assistant_id"`
	TimeoutSeconds int      `json:"timeout_seconds"`
	MaxConcurrency int      `json:"max_concurrency"`
	DataStoreIDs   []string `json:"data_store_ids"`
}

// SLOTargets defines latency thresholds for a probe test case.
type SLOTargets struct {
	MaxTTFTMs float64 `json:"max_ttft_ms"`
	MaxTTFA float64 `json:"max_ttfa_ms,omitempty"`
	MaxTTLT   float64 `json:"max_ttlt_ms"`
}

// Assertions defines semantic and code assertions for evaluating probe success.
type Assertions struct {
	MustContainKeywords []string `json:"must_contain_keywords"`
	ForbiddenErrors     []string `json:"forbidden_errors"`
	MustHaveCitations   bool     `json:"must_have_citations"`
}

// TestCase represents a single synthetic smoke probe scenario.
type TestCase struct {
	ID               string     `json:"id"`
	Module           string     `json:"module"`
	Subsystem        string     `json:"subsystem"`
	Title            string     `json:"title"`
	Query            string     `json:"query"`
	ExpectedBehavior string     `json:"expected_behavior"`
	GroundingType    string     `json:"grounding_type"`
	SLOTargets       SLOTargets `json:"slo_targets"`
	Assertions       Assertions `json:"assertions"`
}

// ProbeResult encapsulates the outcome and telemetry of an executed probe.
type ProbeResult struct {
	ID              string        `json:"id"`
	Title           string        `json:"title"`
	Subsystem       string        `json:"subsystem"`
	Query           string        `json:"query"`
	Passed          bool          `json:"passed"`
	SLOPassed       bool          `json:"slo_passed"`
	StatusCode      int           `json:"status_code"`
	TTFTMs          float64       `json:"ttft_ms"`
	TTFAMs          float64       `json:"ttfa_ms"`
	TotalLatencyMs  float64       `json:"total_latency_ms"`
	HasCitations    bool          `json:"has_citations"`
	FailureReasons  []string      `json:"failure_reasons"`
	ResponsePreview string        `json:"response_preview"`
	ExecutedAt      time.Time     `json:"executed_at"`
}

// ProberReport represents the aggregated JSON report exported by ge-prober.
type ProberReport struct {
	Timestamp        string        `json:"timestamp"`
	ProjectID        string        `json:"project_id"`
	Location         string        `json:"location"`
	EngineID         string        `json:"engine_id"`
	TotalProbes      int           `json:"total_probes"`
	FunctionalPassed int           `json:"functional_passed"`
	SLOPassed        int           `json:"slo_passed"`
	Results          []ProbeResult `json:"results"`
}

// --- StreamAssist REST API Payloads ---

// QueryText represents the query text container.
type QueryText struct {
	Text string `json:"text"`
}

// DataStoreSpec represents a single data store in vertexAiSearchSpec.
type DataStoreSpec struct {
	DataStore string `json:"dataStore"`
}

// VertexAISearchSpec encapsulates data store bindings.
type VertexAISearchSpec struct {
	DataStoreSpecs []DataStoreSpec `json:"dataStoreSpecs,omitempty"`
}

// ToolsSpec encapsulates tools enabled for the query.
type ToolsSpec struct {
	VertexAISearchSpec *VertexAISearchSpec    `json:"vertexAiSearchSpec,omitempty"`
	WebGroundingSpec   map[string]interface{} `json:"webGroundingSpec,omitempty"`
}

// AgentSpec represents an agent targeting specification (e.g. Deep Research).
type AgentSpec struct {
	AgentID string `json:"agentId"`
}

// AgentsSpec represents agent orchestration specs.
type AgentsSpec struct {
	AgentSpecs []AgentSpec `json:"agentSpecs,omitempty"`
}

// SessionInfo represents session continuation context.
type SessionInfo struct {
	Session string `json:"session,omitempty"`
}

// StreamAssistRequest represents the body sent to Discovery Engine StreamAssist.
type StreamAssistRequest struct {
	Query       QueryText    `json:"query"`
	ToolsSpec   *ToolsSpec   `json:"toolsSpec,omitempty"`
	AgentsSpec  *AgentsSpec  `json:"agentsSpec,omitempty"`
	SessionInfo *SessionInfo `json:"sessionInfo,omitempty"`
}

// ContentPart represents an individual reply text chunk.
type ContentPart struct {
	Text    string `json:"text,omitempty"`
	Role    string `json:"role,omitempty"`
	Thought bool   `json:"thought,omitempty"`
}

// GroundedContent encapsulates grounded content part and metadata.
type GroundedContent struct {
	Content          ContentPart            `json:"content"`
	GroundingMetadata map[string]interface{} `json:"groundingMetadata,omitempty"`
}

// ReplyPart encapsulates a single reply from an agent or model.
type ReplyPart struct {
	GroundedContent GroundedContent        `json:"groundedContent"`
	References      []interface{}          `json:"references,omitempty"`
	Citations       []interface{}          `json:"citations,omitempty"`
}

// ContentMetadata encapsulates rich kind metadata (e.g. RESEARCH_PLAN, RESEARCH_QUESTION).
type ContentMetadata struct {
	ContentKind string `json:"contentKind,omitempty"`
}

// AssistAnswer encapsulates the answer object in a streaming chunk.
type AssistAnswer struct {
	State           string          `json:"state,omitempty"`
	Replies         []ReplyPart     `json:"replies,omitempty"`
	ContentMetadata ContentMetadata `json:"contentMetadata,omitempty"`
	ADKAuthor       string          `json:"adkAuthor,omitempty"`
}

// StreamAssistChunk represents a single chunk emitted by the StreamAssist stream.
type StreamAssistChunk struct {
	Answer      AssistAnswer `json:"answer,omitempty"`
	SessionInfo SessionInfo  `json:"sessionInfo,omitempty"`
}
