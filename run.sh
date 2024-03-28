#!/bin/bash

# Doesn't really work for clean shutdowns, but it's a start

# Function to display usage instructions
usage() {
    echo "Usage: $0 [option]"
    echo "Options:"
    echo "  -a, --all         Run all commands (default)"
    echo "  -s, --server      Run the server command"
    echo "  -f, --find        Run the find command"
    echo "  -h, --help        Display this help message"
}

run_server() {
    echo "Running server command..."
    python see_mp/server.py &
}

run_find() {
    echo "Running find command..."
    python see_mp/client.py &
}

# Function to handle the termination of processes
terminate_processes() {
    echo "Terminating processes..."
    # Option 1: Use pkill for pattern matching, if applicable
    pkill -f 'python see_mp/server.py'
    pkill -f 'python see_mp/client.py'

    # # Option 2: Explicitly kill process groups
    # kill -- -$server_pid
    # kill -- -$find_pid

    wait $server_pid $find_pid 2>/dev/null
    exit 0
}

# Register the terminate_processes function to handle SIGINT and SIGTERM
trap terminate_processes SIGINT SIGTERM

# Parse command-line arguments
case "$1" in
    -a|--all)
        run_server
        server_pid=$!
        run_find
        find_pid=$!
        wait $server_pid $find_pid
        ;;
    -s|--server)
        run_server
        server_pid=$!
        wait $server_pid
        ;;
    -f|--find)
        run_find
        find_pid=$!
        wait $find_pid
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        usage
        exit 1
        ;;
esac