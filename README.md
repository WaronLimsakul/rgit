# rgit

A reimplementation of Git's core functionality in Python.

## What?

rgit is a lightweight Python implementation of Git that focuses on reproducing the core functionality of the original version control system. This project includes implementations of Git's fundamental components such as:

- Object storage (blobs, trees, commits)
- Branching and tagging
- Indexing (staging area)
- Basic remote operations (fetch/push)
- Merging with conflict resolution
- Diffing and patching
- Common Git commands (add, commit, checkout, etc.)

## Why?

This project was created to gain a deeper understanding of how Git works internally. By reimplementing Git's core features from scratch, it provides insight into:

- Git's object model and content-addressable storage
- How Git tracks changes and manages history
- The mechanics behind branching, merging, and conflict resolution
- How Git's distributed nature works

Instead of just using Git as a black box, rgit helps you see the internals at work, which can improve your mental model of how version control systems operate.

## Quick Start

### Installation

Clone the repository and install it:

```bash
git clone https://github.com/yourusername/rgit.git
cd rgit
pip install -e .
```

### Basic Usage

Initialize a new repository:

```bash
rgit init
```

Add files to staging:

```bash
rgit add file.txt
```

Commit changes:

```bash
rgit commit -m "Initial commit"
```

## Usage

rgit implements many common Git commands with similar syntax:

### Core Commands

- `rgit init` - Initialize a new repository
- `rgit add <paths>` - Add files to the staging area
- `rgit commit -m <message>` - Commit staged changes
- `rgit status` - Show working tree status
- `rgit log` - Show commit history
- `rgit checkout <commit/branch>` - Switch branches or restore working tree files

### Branching and Tagging

- `rgit branch [branch_name] [start_point]` - List or create branches
- `rgit tag <tag_name> [commit]` - Create a tag
- `rgit merge <commit>` - Merge another branch into your current branch

### Remote Operations

- `rgit fetch <path>` - Download objects from another repository
- `rgit push <remote_path> <branch>` - Update remote references

### Visualization and Diffing

- `rgit diff [--cached] [commit]` - Show changes between commits, commit and working tree, etc.
- `rgit show [commit]` - Show various types of objects
- `rgit k` - Visualize the commit graph using graphviz

### Advanced Operations

- `rgit reset <commit> [--hard]` - Reset current HEAD to the specified state
- `rgit revert <commit>` - Revert changes introduced by a commit
- `rgit merge-base <commit_a> <commit_b>` - Find the common ancestor between two commits

## Example Workflow

```bash
# Initialize a new repository
rgit init

# Create and add a file
echo "Hello, rgit!" > hello.txt
rgit add hello.txt

# Make your first commit
rgit commit -m "Add hello.txt file"

# Create a new branch and switch to it
rgit branch feature
rgit checkout feature

# Make changes
echo "New feature" > feature.txt
rgit add feature.txt
rgit commit -m "Add new feature"

# Switch back to master and merge the feature
rgit checkout master
rgit merge feature

# Visualize your commits
rgit k  # requires graphviz
```

## Dependencies

- Python 3.6+
- Standard libraries: os, hashlib, sys, etc.
- External: graphviz (for visualization with the `k` command)

## Contributing

Contributions to rgit are welcome! Here are some ways you can contribute:

1. **Implement missing Git features**: There are many Git commands and features that could be added.
2. **Improve documentation**: Add more examples or clarify existing documentation.
3. **Fix bugs**: Help identify and fix issues in the codebase.
4. **Performance improvements**: Optimize operations for better performance.

### Development Setup

1. Fork the repository
2. Create a new branch: `git checkout -b my-feature-branch`
3. Make your changes
4. Test your changes
5. Submit a pull request

### Testing

The rgit project doesn't yet have a formal test suite. Contributions that add tests would be particularly valuable.

## Limitations

This is an educational reimplementation of Git and has some limitations compared to the original:

- Performance is not optimized
- Some advanced Git features are not implemented
- Security features may be simplified or missing
- Not intended for production use on critical repositories

---

*rgit is created for educational purposes to understand Git's internal architecture and is not affiliated with or endorsed by Git or its maintainers.*
