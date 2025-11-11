import pandas as pd
from docx import Document
from pathlib import Path
from datetime import datetime
import logging
import shutil
import gc
from xhtml2pdf import pisa
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import re
from tqdm import tqdm
from string import Template

# =============================================================================
# HTML TEMPLATE
# =============================================================================
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: $DEFAULT_FONT_FAMILY;
            font-size: $DEFAULT_FONT_SIZE;
            line-height: $DEFAULT_LINE_HEIGHT;
            color: #000;
        }
        h1, h2, h3 {
            color: #000;
            margin-top: 1.5em;
            margin-bottom: 0.6em;
        }
        h1 { font-size: $HEADING_1_SIZE; font-weight: bold; }
        h2 { font-size: $HEADING_2_SIZE; font-weight: bold; }
        p {
            margin: 0.5em 0;
        }
        strong {
            font-weight: bold;
        }
        ul, ol {
            margin: 0.5em 0;
            padding-left: 2em;
            line-height: $LIST_LINE_HEIGHT;
        }
        li {
            margin: 0.3em 0;
            line-height: $LIST_LINE_HEIGHT;
        }
        a.survey-link {
            color: #0066cc;
            text-decoration: underline;
        }
        a.email-link {
            color: #0066cc;
            text-decoration: underline;
        }
    </style>
</head>
<body>
$HTML_BODY
</body>
</html>
""")

# =============================================================================
# GLOBAL WORKER TEMPLATE CACHE - Optimalisering for multiprocessing
# =============================================================================
_worker_template_cache = None

def init_worker(template_path):
    """
    Initialize worker process with template (called once per worker).
    Dette sparer minnebruk ved å unngå å sende template via pickle til hver worker.
    """
    global _worker_template_cache
    if _worker_template_cache is None:
        _worker_template_cache = load_template_for_worker(template_path)

def load_template_for_worker(template_path):
    """Load and convert template to HTML in worker process."""
    try:
        if Path(template_path).exists() and template_path.endswith(".docx"):
            doc = Document(template_path)
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text
                if text.strip():
                    paragraphs.append(f"<p>{text}</p>")
            body = "
".join(paragraphs)
        else:
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        # Process spacing tags and emails
        body = convert_emails_to_links(body)
        body = process_spacing_tags(body)

        # Bruk Template.substitute() for å sette inn HTML-body
        return HTML_TEMPLATE.substitute(
            DEFAULT_FONT_FAMILY="Helvetica, Arial, sans-serif",
            DEFAULT_FONT_SIZE="11pt",
            DEFAULT_LINE_HEIGHT="1.5",
            LIST_LINE_HEIGHT="1.2",
            HEADING_1_SIZE="14pt",
            HEADING_2_SIZE="12pt",
            HTML_BODY=body
        )
    
    except Exception as e:
        raise Exception(f"Failed to load template in worker: {e}")

def convert_emails_to_links(html_content):
    """Convert email addresses in HTML to clickable mailto: links."""
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'

    def replace_email(match):
        email = match.group(1)
        return f'<a href="mailto:{email}" class="email-link">{email}</a>'

    return re.sub(email_pattern, replace_email, html_content)

def process_spacing_tags(html_content):
    """Process spacing tags from Word document."""
    tag_count = html_content.count('&lt;linjeskift&gt;')
    if tag_count > 0:
        html_content = html_content.replace('&lt;linjeskift&gt;', '<p>&nbsp;</p>')
    return html_content

def process_single_file_worker(row_dict, output_folder, required_placeholders):
    """
    Worker function for parallel processing.
    Bruker cached template fra worker process.
    """
    global _worker_template_cache

    try:
        # Use cached template
        content = _worker_template_cache

        # Replace placeholders
        for placeholder in required_placeholders:
            value = str(row_dict.get(placeholder, ''))

            # Special handling for survey link
            if placeholder.lower() == 'uniksurveylink':
                value = f'<a href="{value}" class="survey-link">{value}</a>'

            content = content.replace(f'[{placeholder}]', value)

        # Generate filename
        filename_tag = str(row_dict['filename_tag'])
        filename_tag_clean = filename_tag.replace('/', '_').replace('\', '_').replace(':', '_')
        filename = f"brakar_opinion_{filename_tag_clean}.pdf"
        pdf_path = os.path.join(output_folder, filename)

        # Create PDF using xhtml2pdf
        with open(pdf_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(
                content.encode('utf-8'),
                dest=pdf_file,
                encoding='utf-8'
            )

        if pisa_status.err:
            return {'success': False, 'error': 'xhtml2pdf conversion failed'}

        return {'success': True, 'filename': filename}

    except Exception as e:
        filename_tag = row_dict.get('filename_tag', 'unknown')
        return {'success': False, 'error': str(e)}

class HTMLPDFGenerator:
    """
    Fast HTML-based PDF generator with parallel processing using xhtml2pdf.
    """

    def __init__(self, template_path, output_folder, required_placeholders, batch_size=2000, num_workers=None):
        self.template_path = str(Path(template_path).resolve())
        self.output_folder = str(Path(output_folder).resolve())
        self.required_placeholders = required_placeholders
        self.batch_size = batch_size
        self.num_workers = num_workers or max(1, multiprocessing.cpu_count() - 1)

        Path(self.output_folder).mkdir(parents=True, exist_ok=True)
        self.cleanup_temp_folders()
        self.setup_logging()

        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }

    def cleanup_temp_folders(self):
        for folder in Path(self.output_folder).glob("temp_*"):
            if folder.is_dir():
                try:
                    shutil.rmtree(folder)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp folder {folder}: {e}")

    def setup_logging(self):
        """Setup logging to file and console."""
        log_filename = os.path.join(
            self.output_folder, 
            f'generation_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Log file created: {log_filename}")

    def process_batch(self, batch_df, batch_num, output_folder):
        self.logger.info(f"
Processing batch {batch_num} ({len(batch_df)} files)...")

        batch_success = 0
        batch_failed = 0

        with ProcessPoolExecutor(
            max_workers=self.num_workers,
            initializer=init_worker,
            initargs=(self.template_path,)
        ) as executor:
            futures = {}
            for idx, row in batch_df.iterrows():
                row_dict = {col: row[col] for col in self.required_placeholders + ['filename_tag']}
                future = executor.submit(
                    process_single_file_worker,
                    row_dict,
                    output_folder,
                    self.required_placeholders
                )
                futures[future] = row.get('filename_tag', idx)

            with tqdm(total=len(futures), desc=f"Batch {batch_num}") as pbar:
                for future in as_completed(futures):
                    filename_tag = futures[future]
                    try:
                        result = future.result()
                        if result['success']:
                            batch_success += 1
                            self.stats['success'] += 1
                        else:
                            batch_failed += 1
                            self.stats['failed'] += 1
                            self.logger.error(f"Failed {filename_tag}: {result.get('error', 'Unknown')}")
                    except Exception as e:
                        batch_failed += 1
                        self.stats['failed'] += 1
                        self.logger.error(f"Failed {filename_tag}: {str(e)}")
                    finally:
                        pbar.update(1)

            self.logger.info(f"Batch {batch_num} complete: {batch_success} success, {batch_failed} failed")
            gc.collect()

            return batch_success, batch_failed

    def generate(self, df, limit_rows=None):
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'start_time': datetime.now(),
            'processing_start_time': None,
            'end_time': None
        }

        self.logger.info(f"
{'='*60}")
        self.logger.info(f"Starting PDF Generation (xhtml2pdf + worker caching)")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Template: {self.template_path}")
        self.logger.info(f"Output: {self.output_folder}")
        self.logger.info(f"Batch size: {self.batch_size}")
        self.logger.info(f"Parallel workers: {self.num_workers}")

        if limit_rows:
            self.logger.info(f"TESTING MODE: Limited to {limit_rows} rows")

        if limit_rows is not None:
            df = df.head(limit_rows)

        self.stats['total'] = len(df)
        self.stats['processing_start_time'] = datetime.now()

        num_batches = (len(df) + self.batch_size - 1) // self.batch_size

        for batch_num in range(num_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min((batch_num + 1) * self.batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]

            self.process_batch(batch_df, batch_num + 1, self.output_folder)

        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['processing_start_time']).total_seconds()
        total_duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        self.logger.info(f"
{'='*60}")
        self.logger.info(f"GENERATION COMPLETE")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total files: {self.stats['total']}")
        self.logger.info(f"Successful: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Processing time: {duration/60:.1f} minutes")
        self.logger.info(f"Total time (incl. data loading): {total_duration/60:.1f} minutes")
        self.logger.info(f"Rate: {self.stats['success']/duration:.2f} files/second")
        self.logger.info(f"{'='*60}")

        return True

# Helper function to load and validate data
def load_and_validate_data(file_path, required_columns, limit_rows=None):
    file_extension = Path(file_path).suffix.lower()
    try:
        if file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(
                file_path,
                usecols=required_columns,
                nrows=limit_rows,
                engine='openpyxl',
                dtype=str
            )
        elif file_extension == '.csv':
            df = pd.read_csv(
                file_path,
                usecols=required_columns,
                nrows=limit_rows,
                dtype=str
            )
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        return df
    except Exception as e:
        raise Exception(f"Error loading and validating data: {e}")

# Example usage
if __name__ == "__main__":
    required_placeholders = ["mic", "navn", "uniksurveylink"]

    # Les inn data
    file_path = "path/to/excel_or_csv_file.xlsx"
    df = load_and_validate_data(file_path, required_columns=required_placeholders + ["filename_tag"])

    # Opprett generator
    generator = HTMLPDFGenerator(
        template_path="path/to/template.docx",
        output_folder="path/to/output/folder",
        required_placeholders=required_placeholders,
        batch_size=2000,
        num_workers=None
    )

    # Generer PDF-er
    generator.generate(df, limit_rows=20)  # Test med 20 rader
