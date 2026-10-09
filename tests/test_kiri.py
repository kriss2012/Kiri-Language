import pytest

from kiri import run_source


def test_print_and_assignment():
    output = run_source('''
        let name = "Kiri";
        print(name);
    ''')
    assert 'Kiri' in output


def test_arithmetic_and_if():
    output = run_source('''
        let x = 2;
        let y = 3;
        let z = x + y * 2;
        if z == 8 {
            print("ok");
        }
    ''')
    assert 'ok' in output


def test_function_call():
    output = run_source('''
        fn add(a, b) {
            return a + b;
        }
        print(add(2, 3));
    ''')
    assert '5' in output


def test_logical_operators_short_circuit():
    output = run_source('''
        print(false and missing_name);
        print(true or missing_name);
    ''')
    assert output.splitlines() == ['False', 'True']
