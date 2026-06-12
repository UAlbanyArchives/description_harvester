from unittest.mock import Mock

import description_harvester.__init__ as cli


def test_commit_commits_solr(monkeypatch, capsys):
    mock_solr = Mock()

    monkeypatch.setattr(cli.pysolr, "Solr", Mock(return_value=mock_solr))

    cli.harvest(["--commit"])

    mock_solr.ping.assert_called_once_with()
    mock_solr.commit.assert_called_once_with()
    output = capsys.readouterr().out
    assert "Committing all collection docs to the Solr index..." in output


def test_commit_must_be_standalone(monkeypatch, capsys):
    solr_constructor = Mock()

    monkeypatch.setattr(cli.pysolr, "Solr", solr_constructor)

    cli.harvest(["--commit", "--id", "apap101"])

    solr_constructor.assert_not_called()
    output = capsys.readouterr().out
    assert "--commit must be used on its own after one or more --batch runs." in output