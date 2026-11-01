from tandembench.runner import main

if __name__ == '__main__':
    import sys
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('Interrupted; recorded responses are preserved. Resume with the same settings.',file=sys.stderr)
        sys.exit(130)
    except (ValueError, OSError) as exc:
        print(f'Evaluation stopped: {exc}',file=sys.stderr)
        sys.exit(2)
