from mock import Mock

from datarunner import Workflow, Flow, Step


def test_step():
    class Count(Step):
        def run(self):
            return [1, 2, 3]

    count = Count()
    assert count() == [1, 2, 3]       # Callable
    assert count.run() == [1, 2, 3]   # Runnable
    assert list(count) == [1, 2, 3]   # Iterable

    assert Step(lambda: 1).name == '<lambda>'
    assert Step(print).name == 'print'
    assert Step(Mock(name='mocked')).name == 'mocked'

    class Step1(Step):
        pass
    assert Step.instance(Step1()).name == 'Step1'

    class Step2(Step):
        def __str__(self):
            return 'Super Step'
    assert Step.instance(Step2()).name == 'Super Step'

    class Step3(Step):
        name = "Fast Step"
    assert Step.instance(Step3()).name == 'Fast Step'


def test_flow(capsys):
    flow = Flow(range(3), print)
    assert len(flow) == 2

    flow >> range(6) >> print
    assert len(flow) == 4

    flow()
    out, err = capsys.readouterr()
    print(out)
    assert """\
range(0, 3)
>> print
range(0, 3)
>> range(0, 6)
>> print
range(0, 6)
""" == out


def test_workflow_basics(capsys):
    class Load(Step):
        def __repr__(self):
            return 'Load("dest")'

        def run(self, num):
            return num * 2

    class Finish(Step):
        def run(self):
            print('finished')

    transform = Mock(name='transform', return_value=3)
    flow = Workflow(lambda: print("started"),
                    [lambda: 1, transform, Load()],
                    etl=[lambda: 2, transform, Load()],
                    )

    result = flow.run()

    transform.assert_called_with(2)
    assert result == 6

    out, err = capsys.readouterr()
    print(out)
    assert """\
<lambda>
started

<lambda>
>> transform
>> Load("dest")

etl
--------------------------------------------------------------------------------
<lambda>
>> transform
>> Load("dest")
""" == out

    print(flow)
    assert """\
<lambda>

<lambda>
>> transform
>> Load("dest")

etl
--------------------------------------------------------------------------------
<lambda>
>> transform
>> Load("dest")""" == str(flow)


def test_workflow_as_flow(capsys):
    flow = Workflow() >> range(3) >> print >> range(6) >> print
    flow.run()

    out, err = capsys.readouterr()
    print(out)

    assert len(flow) == 0
    assert len(flow.flows) == 1

    assert """\
range(0, 3)
>> print
range(0, 3)
>> range(0, 6)
>> print
range(0, 6)
""" == out

    flow = Workflow(name='named') >> 1 >> print
    assert """\
named
--------------------------------------------------------------------------------
1
>> print""" == str(flow)


def test_workflow_with_flow(capsys):
    Workflow(
        Flow() >> range(3) >> print,
        another=Flow() >> range(6) >> print).run()

    out, err = capsys.readouterr()
    print(out)

    assert """\
range(0, 3)
>> print
range(0, 3)

another
--------------------------------------------------------------------------------
range(0, 6)
>> print
range(0, 6)
""" == out


def test_workflow_templates():
    class TemplatedStep(Step):
        TEMPLATE_ATTRS = ['query']

        def __init__(self, query):
            super().__init__()
            self.query = query

        def run(self):
            return self.query

    flow = Workflow() >> TemplatedStep('SELECT * FROM {dataset}.table')
    result = flow.run(dataset='foo')

    assert result == 'SELECT * FROM foo.table'


def test_readme(capsys):
    def setup():
        print('Ready to go!')

    def extract():
        return 'data'

    def transform(data):
        return data + ' using reusable code pieces, like Lego.'

    class Load(Step):
        """ Sub-class Step to customize the callable """
        def __init__(self, destination):
            super().__init__()
            self.destination = destination

        def __str__(self):
            return f'Load("{self.destination}")'

        def run(self, data):
            print(f'Loading {data}')

    flow = Workflow(setup,
                    table_name1=[extract, transform, Load('example')])
    flow.run()

    print()
    flow = Workflow() >> extract >> transform >> Load('example')
    flow.run()

    out, err = capsys.readouterr()
    print(out)
    assert """\
setup
Ready to go!

table_name1
--------------------------------------------------------------------------------
extract
>> transform
>> Load("example")
Loading data using reusable code pieces, like Lego.

extract
>> transform
>> Load("example")
Loading data using reusable code pieces, like Lego.
""" == out

    class Load(Step):
        TEMPLATE_ATTRS = ['destination']

        """ Sub-class Step to customize the callable """
        def __init__(self, destination):
            super().__init__()
            self.destination = destination

        def __str__(self):
            return f'Load("{self.destination}")'

        def run(self, data):
            print(f'Loading {data}')

    flow = Workflow() >> extract >> transform >> Load('{dataset}.table_name1')
    flow.run(dataset='staging')

    out, err = capsys.readouterr()
    print(out)
    assert """\
setup
Ready to go!

table_name1
--------------------------------------------------------------------------------
extract
>> transform
>> Load("example")
Loading data using reusable code pieces, like Lego.

extract
>> transform
>> Load("example")
Loading data using reusable code pieces, like Lego.

extract
>> transform
>> Load("staging.table_name1")
Loading data using reusable code pieces, like Lego.
""" == out

    print(flow)
    assert """\
extract
>> transform
>> Load("staging.table_name1")""" == str(flow)
