import datetime,json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'scripts'))
from ai_office_sources import files_under,collect_reports,chunks
from ai_office_sync import item,clean
class SourceTests(unittest.TestCase):
 def test_empty_unavailable_and_all_chunks(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):files_under(tmp)
   with self.assertRaises(FileNotFoundError):files_under(pathlib.Path(tmp)/'missing')
  long='正文'*40000;self.assertEqual(''.join(chunks(long)),long)
 def test_report_comments_original_dates_and_duplicates(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);folder=root/'wecom/report';folder.mkdir(parents=True)
   rows=[{'journal_uuid':'stable-'+str(i),'report_time':1791777600,'template_name':'隔离日报','submitter':{'userid':'test-person'},'apply_data':{'contents':[{'title':[{'text':'今日未完成事项'}],'value':{'text':'长正文'*9000+'<img src="test-inert">'}}]},'comments':[{'content':'评论更正：已完成','comment_userinfo':{'userid':'reviewer'},'comment_time':1791778600}]} for i in range(15)]
   text='```json\n'+json.dumps(rows,ensure_ascii=False)+'\n```';(folder/'part-1.md').write_text(text);(folder/'duplicate.md').write_text(text)
   items,status=collect_reports(root,item,clean,datetime.datetime(2026,10,13,tzinfo=datetime.timezone(datetime.timedelta(hours=8))))
   self.assertEqual(status['count'],15);self.assertEqual(status['comments'],15);self.assertEqual(status['imagesNotRead'],15);self.assertTrue(len(items)>15);self.assertTrue(any('reviewer' in t['note'] and '已完成' in t['note'] for t in items));self.assertTrue(all(t['sourceDate'].startswith('2026-10-12') for t in items));self.assertTrue(all(t['sourcePath'] for t in items))
if __name__=='__main__':unittest.main()
