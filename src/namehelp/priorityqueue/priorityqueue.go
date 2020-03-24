// copied almost verbatum from

package priorityqueue

import "container/heap"

// An Item is something we manage in a priority queue.
type Item struct {
	Value    string // The value of the item; arbitrary.
	Priority int    // The priority of the item in the queue.

	// The index is needed by update and is maintained by the heap.Interface methods.
	index int // The index of the item in the heap.
}

// A MaxPriorityQueue implements heap.Interface and holds Items.
type MaxPriorityQueue []*Item

func (priorityQueue MaxPriorityQueue) Len() int {
	return len(priorityQueue)
}

func (priorityQueue MaxPriorityQueue) Less(i, j int) bool {
	// We want Pop to give us the highest priority so Less is actually >.
	return priorityQueue[i].Priority > priorityQueue[j].Priority
}

func (priorityQueue MaxPriorityQueue) Swap(i, j int) {
	priorityQueue[i], priorityQueue[j] = priorityQueue[j], priorityQueue[i]
	priorityQueue[i].index = i
	priorityQueue[j].index = j
}

// Push adds x as element at index = Len()
// This is for package heap's implementation to call
func (priorityQueue *MaxPriorityQueue) Push(x interface{}) {
	n := priorityQueue.Len()
	item := x.(*Item) // convert interface to *Item
	item.index = n
	*priorityQueue = append(*priorityQueue, item)
}

// Pop remove and return element at index = Len() - 1
// This is for package heap's implementation to call
func (priorityQueue *MaxPriorityQueue) Pop() interface{} {
	old := *priorityQueue
	n := old.Len()
	item := old[n-1]
	item.index = -1 // for safety
	*priorityQueue = old[0 : n-1]
	return item
}

// TrimLowestItems eliminates k items from the back of the queue
func (priorityQueue *MaxPriorityQueue) TrimLowestItems(k int) {
	old := *priorityQueue
	oldLength := old.Len()

	for i := 0; i < k; i++ {
		item := old[oldLength-1-i]
		item.index = -1 // for safety
	}

	*priorityQueue = old[0 : oldLength-k]
}

// Update modifies the priority and value of an Item in the queue.
func (priorityQueue *MaxPriorityQueue) Update(item *Item, value string, priority int) {
	item.Value = value
	item.Priority = priority
	heap.Fix(priorityQueue, item.index)
}

// Find does a linear search through the priority queue for an Item whose value equals searchValue.
// O(n)
func (priorityQueue *MaxPriorityQueue) Find(searchValue string) *Item {
	for _, item := range *priorityQueue {
		if item.Value == searchValue {
			return item
		}
	}
	return nil
}
