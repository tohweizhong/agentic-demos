package main

import (
	"errors"
	"sync"
	"testing"
)

func TestNewStoreHasSeedItems(t *testing.T) {
	s := NewStore()
	got, err := s.Get("ITEM-001")
	if err != nil {
		t.Fatalf("Get(ITEM-001) returned error: %v", err)
	}
	if got.Status != "open" {
		t.Errorf("Get(ITEM-001).Status = %q, want %q", got.Status, "open")
	}
}

func TestGetUnknownItem(t *testing.T) {
	s := NewStore()
	_, err := s.Get("ITEM-999")
	if !errors.Is(err, ErrNotFound) {
		t.Errorf("Get(ITEM-999) error = %v, want ErrNotFound", err)
	}
}

func TestUpdateChangesStatus(t *testing.T) {
	s := NewStore()
	got, err := s.Update("ITEM-002", "closed")
	if err != nil {
		t.Fatalf("Update returned error: %v", err)
	}
	if got.Status != "closed" {
		t.Errorf("Update().Status = %q, want %q", got.Status, "closed")
	}
	again, _ := s.Get("ITEM-002")
	if again.Status != "closed" {
		t.Errorf("Get after Update: Status = %q, want %q", again.Status, "closed")
	}
}

func TestUpdateRejectsBadStatus(t *testing.T) {
	s := NewStore()
	_, err := s.Update("ITEM-001", "deleted")
	if !errors.Is(err, ErrBadStatus) {
		t.Errorf("Update with bad status: error = %v, want ErrBadStatus", err)
	}
}

func TestUpdateUnknownItem(t *testing.T) {
	s := NewStore()
	_, err := s.Update("ITEM-999", "closed")
	if !errors.Is(err, ErrNotFound) {
		t.Errorf("Update(ITEM-999) error = %v, want ErrNotFound", err)
	}
}

func TestStoreIsSafeForConcurrentUse(t *testing.T) {
	s := NewStore()
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(2)
		go func() { defer wg.Done(); _, _ = s.Update("ITEM-001", "in_progress") }()
		go func() { defer wg.Done(); _, _ = s.Get("ITEM-001") }()
	}
	wg.Wait()
}
