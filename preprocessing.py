import numpy as np
import pandas as pd
import os
import re
import us
from collections import OrderedDict
from tqdm import tqdm, tqdm_notebook


state_names = [state.name for state in us.states.STATES_AND_TERRITORIES]
state_names.remove('Orleans')


def read_all_files(in_path):
    """Read all the files and put the data into a DataFrame."""
    # For errors from the pdf parsing utility
    error_to_col = {'Ad I D': 'Ad ID'}
    # Set up the dataframe
    cols = ['Ad ID', 'Ad Text', 'Ad Landing Page', 'Ad Targeting Location',
            'Excluded Connections', 'Age', 'Language', 'Placements',
            'People Who Match', 'Ad Impressions', 'Ad Clicks',
            'Ad Spend', 'Ad Creation Date', 'Ad End Date', 'time_period']
    df = pd.DataFrame(columns=cols)

    # Go through all folders/files and extract the data
    folders = os.listdir(in_path)
    for folder in tqdm_notebook(folders):
        tqdm.write(f"Processing Folder: {folder}")
        curr_path = f'{in_path}{folder}/'
        files = os.listdir(curr_path)
        for file in files:
            # Set up row for this data
            new_row = pd.Series(index=cols)
            new_row['time_period'] = folder
            name = file.split('.')[0]
            
            # Read through the file
            with open(f'{curr_path}{file}', 'r', encoding='utf-8') as f:
                for line in f:
                    if len(line.strip()) == 0:
                        break  # We are through all the lines
                    for c in cols:
                        if c in line:
                            break  # A succesful match
                    else:  # Finally, if no match - check for errors
                        c = None
                        # Double check that it wasn't parsed poorly
                        for k, v in error_to_col.items():
                            if k in line:
                                c = v
                                break
                    # If no match, append to old line
                    if c == None:
                        clean_line = line.strip()
                        old_line = new_row[last_c]
                        if last_c != 'Ad ID':  # Sometimes we miss Ad Text
                            new_row[last_c] = ' '.join([old_line, clean_line])
                        else:
                            new_row['Ad Text'] = clean_line
                    else:
                        clean_line = line.replace(c, '')[1:].strip()
                        new_row[c] = clean_line
                        last_c = c
            df.loc[name, :] = new_row
    return df


def clean_ad_id(ad_id):
    """Clean the ad_id."""
    if len(ad_id) > 5:
        ad_id = ad_id[6:]
    return int(ad_id)


class AdTgtLocCleaner:

    def __init__(self):
        # Different forms of data which can be stored in the ad location field
        self.headers = OrderedDict({
            'countries': 'UnusedValue:',
            'states': 'UnusedValue:',
            'locs': '- Living In:',
            'exc_states': 'Exclude Location:',
            'interests': 'Interests:',
            'connections': 'Connections:',
            'friend_connections': 'Friends of connections:',
            'behaviors': 'Behaviors:',
            'generation': 'Generation:',
            'politics': 'Politics:'})

    def clean(self, ad_loc, return_type='as_array'):
        """Clean the ad targeting location data field.

        A warning to all those who find themselves here:
        The following code is an obscure mess of parsing some
        data that is itself in an obscure mess of a format.
        I tried to write this code replete with comments, lest
        some unfortunate soul wanders in. If you find yourself,
        I give you this one last warning: turn back.
        """
        # Preliminary corner-case cleaning
        ad_loc = ad_loc.replace('- Recently In', '- Living In')

        # Set up output, check if there is no info
        output = OrderedDict({k: [] for k in self.headers.keys()})
        if ad_loc == 'None':
            if return_type == 'as_dict':
                return output
            elif return_type =='as_array':
                return [v for v in output.values()]

        # First parse the locations of the headers
        header_locs = {}
        for name, string in self.headers.items():
            if string in ad_loc:
                i_loc = ad_loc.index(string)
                header_locs[name] = (i_loc, i_loc + len(string))

        # Now reverse into an ordered dict
        idx_dict = OrderedDict({v: k for k,v in header_locs.items()})

        # Now get the interveneing text indexes
        text_idx_dict = {}
        last_header = None
        is_first = True
        for idx_pair, header in idx_dict.items():
            # Locations are always first if we dont have a header
            if is_first:
                is_first = False
                if idx_pair[0] != 0:
                    text_idx_dict['locs'] = (0, idx_pair[0])
            else:  # If we are at least 2nd, get post-header text
                text_idx_dict[last_header] = (start, idx_pair[0]-1)
            last_header = header
            start = idx_pair[1]
        else:  # Finally get indexes for the last header
            if last_header == None:
                # If there were no headers, its just a location
                text_idx_dict['locs'] = (0, len(ad_loc))
            else:
                text_idx_dict[last_header] = (start, len(ad_loc))
        
        # Slice out the text into a dict
        text_dict = {}
        for name, idxs in text_idx_dict.items():
            text_dict[name] = ad_loc[idxs[0]:idxs[1]]

        # Parse text into the output
        # Clean locations
        countries, states, locs = self._clean_location_data('locs', text_dict)
        output['countries'] = countries
        output['states'] = states
        output['locs'] = locs
        
        # Clean the excluded locations
        _, exc_locs, _ = self._clean_location_data('exc_states', text_dict)
        output['exc_states'] = exc_locs

        # Clean all the data that was in list format
        keys = ['interests', 'behaviors', 'connections', 'friend_connections',
                'generation', 'politics']
        for key in keys:
            output[key] = self._clean_list_data(key, text_dict)

        if return_type == 'as_dict':
            return output
        elif return_type =='as_array':
            return [v for v in output.values()]

    def _clean_location_data(self, key, text_dict):
        """Clean location data from ad_tgt_loc."""
        countries = []
        states = []
        locs = []
        if key in text_dict.keys():
            loc_text = text_dict[key]
            loc_text = loc_text.replace('United States ', 'United States: ')
            if ':' in loc_text:
                loc_list = [*loc_text.split(':')]
                countries = [loc_list[0].strip()]
                locs = ', '.join(l.strip() for l in loc_list[1:])
                states = []
                for s in state_names:
                    if s in locs:
                        states.append(s)
                        if s != 'New York':
                            locs = locs.replace(s, '')
                locs = locs.replace(' (', '(').replace('(', ' (')
                locs = [*map(lambda s: s.strip(), re.split('[,;]', locs))]
                locs = [l for l in locs if l != '']
            else:  # We just have countries
                countries = [*map(lambda s: s.strip(), loc_text.split(','))]
        
        return countries, states, locs

    def _clean_list_data(self, key, text_dict):
        """Clean data that was in a list format."""
        if key in text_dict.keys():
            list_text = text_dict[key]
            if ' or ' in list_text:
                items = [*list_text.split(' or ')]
                i0 = ' or '.join(items[:-1])
                i1 = [items[-1].strip()]
                parsed_list = re.split('[,.;]', i0) + i1
            else:
                parsed_list = list_text.split(', ')
            parsed_list = [*map(lambda s: s.strip(), parsed_list)]
            parsed_list = [p for p in parsed_list if p not in ['', 'Jr']]
        else:
            parsed_list = []
        return parsed_list


class PeopleWhoMatchCleaner(AdTgtLocCleaner):

    def __init__(self):
        self.headers = OrderedDict({
            'interests': 'Interests:',
            'friend_connections': 'Friends of connections:',
            'behaviors': 'Behaviors:',
            'page_likes': 'People who like',
            'politics': 'Politics:'})

    def _clean(self, ad_loc, return_type='as_array'):
        """Small wrapper to first clean the strings."""
        # TODO: abstract out the common cleaning, and make the local .clean
        # functions parse out the appropriate keys
        ad_loc = ad_loc.replace('And Must Also Match:', '')
        return self.clean(ad_loc, return_type)


def parse_ad_targeting_location(df):
    """Parse the ad targeting location column, and add it to the DataFrame."""
    # First parse all the data
    cleaner = AdTgtLocCleaner()
    parsed_arr = np.array([cleaner.clean(ad_text) for ad_text
                           in df['ad_targeting_location']])
    # Now add it to new columns in the DataFrame
    new_cols = ['countries', 'states', 'locs', 'exc_states', 'interests',
                'connections', 'friend_connections', 'behaviors', 'generation',
                'politics']
    return df.join(pd.DataFrame(parsed_arr, df.index, new_cols))


def parse_people_who_match(df):
    """Parse the ad targeting location column, and add it to the DataFrame."""
    # First parse all the data
    cleaner = PeopleWhoMatchCleaner()
    parsed_arr = np.array([cleaner._clean(ad_text, 'as_dict') for ad_text
                           in df['people_who_match']])
    # Now add it to new columns in the DataFrame
    new_cols = ['interests2', 'friend_connections2', 'behaviors2',
                'page_likes']
    return parsed_arr
    return df.join(pd.DataFrame(parsed_arr, df.index, new_cols))


# Utility function for easy viewing
def sample_loc(s, df, n=10, shuffle=False):
    """Sample locs that contain s."""
    msk = df['ad_targeting_location'].apply(lambda v: s in v)
    r_val = df['ad_targeting_location'][msk]
    if not shuffle:
        return r_val[:n].values
    else:
        return r_val.sample(n).values

# Utility function for easy viewing
def sample_like(s, df, n=10, shuffle=False):
    """Sample locs that contain s."""
    msk = df['people_who_match'].apply(lambda v: s in v)
    r_val = df['people_who_match'][msk]
    if not shuffle:
        return r_val[:n].values
    else:
        return r_val.sample(n).values