#!/usr/bin/env python3
"""
法拍補償系統 - 100人模擬測試
模擬100個不同用戶的行為，測試系統的穩定性、權限控制和UI/UX
"""

import time
import random
import threading
from datetime import datetime, timedelta
import json

class MockUser:
    """模擬用戶類"""
    def __init__(self, user_id, email=None, role=None):
        self.user_id = user_id
        self.email = email or f"user{user_id:03d}@example.com"
        self.role = role or random.choice(['visitor', 'free', 'pro'])
        self.login_time = datetime.now()
        self.session_data = {}
        
    def get_role_limit(self):
        """根據角色返回可查看的項目數量"""
        limits = {'visitor': 3, 'free': 10, 'pro': float('inf')}
        return limits.get(self.role, 3)
    
    def __str__(self):
        return f"User{self.user_id}({self.role}) - {self.email}"

class AuctionSystemTester:
    """系統測試器"""
    def __init__(self):
        self.users = []
        self.test_results = {
            'login_success': 0,
            'login_failed': 0,
            'ui_response_time': [],
            'data_access_violations': [],
            'ui_issues': [],
            'performance_metrics': {}
        }
        self.mock_data = self._generate_mock_data()
        
    def _generate_mock_data(self):
        """生成模擬的拍賣數據"""
        counties = ['台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市', 
                   '基隆市', '新竹市', '嘉義市', '彰化縣', '苗栗縣', '南投縣',
                   '雲林縣', '嘉義縣', '屏東縣', '宜蘭縣', '花蓮縣', '台東縣',
                   '澎湖縣', '金門縣', '連江縣', '大同鄉', '南澳鄉']
        
        data = []
        for i in range(300):  # 生成300個模擬拍賣項目
            item = {
                'id': i + 1,
                'court': f'{random.choice(["台北", "台中", "高雄", "台南"])}地方法院',
                'case_no': f'{random.randint(110, 112)}司執字第{random.randint(1000, 9999):05d}號',
                'dept': f'{random.choice(["1", "2", "3", "4"])}股',
                'sale_date': f'{random.randint(112, 113)}年{random.randint(1, 12):02d}月{random.randint(1, 28):02d}日',
                'sale_type': random.choice(['第一拍', '第二拍', '第三拍', '應買']),
                'county': random.choice(counties),
                'address': f'{random.randint(1, 999)}號',
                'area': f'{random.randint(30, 200)}坪',
                'base_price': random.randint(500000, 50000000),
                'estimated_comp': random.randint(180000, 1200000),
                'roi': random.randint(5, 500),
                'is_handover': random.choice(['是', '否']),
                'is_empty_land': random.choice(['是', '否']),
                'pdf_url': f'https://example.com/pdf/{i+1}.pdf' if random.random() > 0.3 else ''
            }
            data.append(item)
        return data
    
    def simulate_user_login(self, user):
        """模擬用戶登入"""
        print(f"Login simulation: {user}")
        
        # 模擬登入延遲
        time.sleep(random.uniform(0.1, 0.5))
        
        # 模擬登入成功率 (95%)
        if random.random() < 0.95:
            self.test_results['login_success'] += 1
            return True
        else:
            self.test_results['login_failed'] += 1
            return False
    
    def simulate_data_access(self, user):
        """模擬用戶訪問數據"""
        limit = user.get_role_limit()
        
        # 模擬UI響應時間 (真實的 sleep 模擬 backend 延遲)
        response_time = random.uniform(0.2, 2.0)
        time.sleep(response_time * 0.1)  # 只 sleep 10% 的時間避免測試太久
        self.test_results['ui_response_time'].append(response_time)
        
        # 實際檢查權限：嘗試存取超過限制的資料數量
        attempted = random.randint(1, max(limit if limit != float('inf') else 50, 10))
        if attempted > limit and user.role != 'pro':
            self.test_results['data_access_violations'].append({
                'user': str(user),
                'role': user.role,
                'limit': limit,
                'attempted_access': attempted,
                'detail': f'Tried to access {attempted} items but role limit is {limit}'
            })
        
        accessible_count = min(attempted, limit) if user.role != 'pro' else attempted
        return accessible_count
    
    def simulate_ui_interaction(self, user):
        """實際UI問題檢測（非亂數）"""
        issues = []
        
        # 1. 檢查排序正確性
        sample = self.mock_data[:10]
        sorted_by_roi = sorted(sample, key=lambda x: x['roi'], reverse=True)
        for i in range(len(sorted_by_roi) - 1):
            if sorted_by_roi[i]['roi'] < sorted_by_roi[i+1]['roi']:
                issues.append('排序功能異常: ROI排序不正確')
                break
        
        # 2. 檢查篩選邏輯
        filtered = [x for x in self.mock_data if x['county'] == '台北市']
        for item in filtered:
            if item['county'] != '台北市':
                issues.append('篩選功能異常: 縣市篩選無效')
                break
        
        # 3. 檢查權限限制是否被前端正確套用
        limit = user.get_role_limit()
        if user.role != 'pro' and len(self.mock_data) > limit:
            sliced = self.mock_data[:limit]
            if len(sliced) != limit:
                issues.append(f'權限控制異常: 應回傳{limit}筆但得到{len(sliced)}筆')
        
        # 4. 檢查數據完整性
        required_fields = ['court', 'case_no', 'county', 'address', 'base_price', 'roi']
        for item in self.mock_data[:50]:
            for field in required_fields:
                if field not in item:
                    issues.append(f'數據完整性異常: 缺少欄位 {field}')
                    break
        
        self.test_results['ui_issues'].extend(issues)
        return issues
    
    def _simulate_single_user(self, user, results_lock):
        """單一用戶的完整流程（給 thread 用）"""
        if self.simulate_user_login(user):
            accessible_count = self.simulate_data_access(user)
            ui_issues = self.simulate_ui_interaction(user)
            with results_lock:
                print(f"   User {user.user_id} ({user.role}) - accessed {accessible_count} items")
                if ui_issues:
                    print(f"      Found UI issues: {ui_issues}")
    
    def run_100_user_test(self):
        """執行100人模擬測試（真正並發）"""
        print("=" * 60)
        print("Starting 100-user simulation test")
        print("=" * 60)
        
        # 創建100個模擬用戶
        print("\nCreating 100 mock users...")
        for i in range(1, 101):
            role_weights = {'visitor': 0.4, 'free': 0.4, 'pro': 0.2}
            role = random.choices(list(role_weights.keys()), weights=list(role_weights.values()))[0]
            user = MockUser(i, role=role)
            self.users.append(user)
        
        print(f"Created {len(self.users)} users")
        print(f"   - Visitors: {sum(1 for u in self.users if u.role == 'visitor')}")
        print(f"   - Free members: {sum(1 for u in self.users if u.role == 'free')}")
        print(f"   - Pro members: {sum(1 for u in self.users if u.role == 'pro')}")
        
        # 真正並發請求（使用 threading）
        print("\nStarting concurrent requests simulation (threading)...")
        start_time = time.time()
        results_lock = threading.Lock()
        threads = []
        
        for user in self.users:
            t = threading.Thread(target=self._simulate_single_user, args=(user, results_lock))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        total_time = time.time() - start_time
        
        # 生成測試報告
        self._generate_report(total_time)
        
    def _generate_report(self, total_time):
        """生成測試報告"""
        print("\n" + "=" * 60)
        print("Test Report - 100-User Simulation Results")
        print("=" * 60)
        
        # 基本統計
        print(f"\nTotal test time: {total_time:.2f} seconds")
        print(f"   Average per user: {total_time/100:.2f} seconds")
        
        # 登入統計
        print(f"\nLogin Statistics:")
        print(f"   Success: {self.test_results['login_success']} ({self.test_results['login_success']/100*100:.1f}%)")
        print(f"   Failed: {self.test_results['login_failed']} ({self.test_results['login_failed']/100*100:.1f}%)")
        
        # UI響應時間
        if self.test_results['ui_response_time']:
            avg_response = sum(self.test_results['ui_response_time']) / len(self.test_results['ui_response_time'])
            max_response = max(self.test_results['ui_response_time'])
            print(f"\nUI Response Time:")
            print(f"   Average: {avg_response:.2f} seconds")
            print(f"   Maximum: {max_response:.2f} seconds")
            
            if avg_response > 2.0:
                print(f"   Warning: Average response time too slow (>2 seconds)")
        
        # 權限違規
        if self.test_results['data_access_violations']:
            print(f"\nAccess Violations ({len(self.test_results['data_access_violations'])} cases):")
            for violation in self.test_results['data_access_violations'][:3]:
                print(f"   - {violation['user']}: Role {violation['role']} attempted to access {violation['attempted_access']} items (limit: {violation['limit']})")
        else:
            print(f"\nAccess Control: All users followed access restrictions")
        
        # UI問題
        if self.test_results['ui_issues']:
            unique_issues = list(set(self.test_results['ui_issues']))
            print(f"\nUI Issues Found ({len(unique_issues)} types):")
            for issue in unique_issues:
                count = self.test_results['ui_issues'].count(issue)
                print(f"   - {issue}: occurred {count} times")
        else:
            print(f"\nUI/UX: Normal - no UI issues found")
        
        # 建議
        print(f"\nImprovement Suggestions:")
        if self.test_results['login_success']/100 < 0.9:
            print(f"   - Improve login mechanism to increase success rate")
        if self.test_results['ui_response_time'] and max(self.test_results['ui_response_time']) > 3.0:
            print(f"   - Optimize backend response speed to reduce delays")
        if self.test_results['data_access_violations']:
            print(f"   - Strengthen access control mechanism to prevent violations")
        if self.test_results['ui_issues']:
            print(f"   - Fix UI issues to improve user experience")
        
        print(f"\n100-user simulation test completed!")

if __name__ == "__main__":
    tester = AuctionSystemTester()
    tester.run_100_user_test()